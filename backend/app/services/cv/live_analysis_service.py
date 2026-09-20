"""
Live analysis service coordinating continuous frame acquisition and CV pipeline execution.
Phase 21: Live Traffic Monitoring & Camera Source Management.

REUSES:
- YOLOVehicleDetector
- ByteTrackVehicleTracker
- LineCrossingCounter
- LaneAssignmentEngine / LaneAnalyzer
- TrafficMetricsEngine
- AnalysisPersistenceService persistence schema & child records

DOES NOT:
- Fabricate metrics or fake real-world camera feeds.
- Duplicate inference pipelines.
- Store unbounded video or raw frames to disk.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.logging import get_logger
from app.models.analysis import (
    AnalysisSession,
    CrossingEventRecord,
    LaneResultRecord,
    TrafficMetricsRecord,
)
from app.models.analysis_job import AnalysisJob, JobStatus
from app.models.camera_source import CameraSource, CameraSourceStatus
from app.schemas.counting import CountingLineSchema, Point2DSchema
from app.schemas.lane_analysis import LaneRegionSchema
from app.services.cv.camera_source_adapter import BaseCameraSource, create_camera_source
from app.services.cv.detector import Detector, YOLOVehicleDetector
from app.services.cv.lane_analyzer import LaneAnalyzer, LaneAssignmentEngine, LaneRegion
from app.services.cv.traffic_metrics_engine import (
    TrafficMetricsEngine,
    VideoCountingOutput,
)
from app.services.cv.tracker import (
    ByteTrackVehicleTracker,
    TrackState,
    Tracker,
)
from app.services.cv.vehicle_counter import CountingLine, LineCrossingCounter, Point2D

logger = get_logger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class LiveMetricsSnapshot:
    """Current in-memory live metrics snapshot for polling."""
    camera_source_id: str
    job_id: str
    job_status: str
    is_live: bool
    source_type: str
    source_fps: float
    processing_fps: float
    frames_acquired: int
    frames_processed: int
    dropped_frames: int
    reconnect_count: int
    total_volume: int
    inbound_volume: int
    outbound_volume: int
    active_tracks_count: int
    class_distribution: Dict[str, int]
    direction_distribution: Dict[str, int]
    lane_occupancies: Dict[str, int]
    lane_densities: Dict[str, float]
    provenance_tag: str
    last_frame_timestamp: Optional[float]
    last_updated: datetime
    error_message: Optional[str] = None


class LiveAnalysisService:
    """
    Executes a continuous live analysis loop around a camera source.
    Safely captures frames, executes detection, tracking, counting, and lane analysis,
    maintains bounded preview buffers, and persists aggregate state upon job stop.
    """

    def __init__(
        self,
        job_id: str,
        camera_source_id: str,
        source_type: str,
        connection_uri: str,
        camera_name: str,
        config: Optional[Dict[str, Any]] = None,
        session_factory: Optional[Callable[[], Session]] = None,
    ):
        self.job_id = job_id
        self.camera_source_id = camera_source_id
        self.source_type = source_type
        self.connection_uri = connection_uri
        self.camera_name = camera_name
        self.config = config or {}
        self._session_factory = session_factory

        # Threading & lifecycle
        self._lock = threading.Lock()
        self._stop_requested = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

        # Preview frame buffer (single JPEG byte array)
        self._latest_preview_jpeg: Optional[bytes] = None

        # Metrics snapshot
        self._metrics_lock = threading.Lock()
        self._last_snapshot: Optional[LiveMetricsSnapshot] = None

        # Counters & timing
        self._start_time: Optional[float] = None
        self._frames_processed = 0
        self._total_detections = 0
        self._current_processing_fps = 0.0
        self._last_error: Optional[str] = None

        # Determine provenance
        if self.source_type == "test_fixture":
            self.provenance_category = "test_fixture_observation"
            self.is_synthetic = True
        elif self.source_type in ("local_camera", "rtsp"):
            self.provenance_category = "live_observation"
            self.is_synthetic = False
        else:
            self.provenance_category = "unverified_live"
            self.is_synthetic = False

        # Initial metrics snapshot
        self._last_snapshot = LiveMetricsSnapshot(
            camera_source_id=self.camera_source_id,
            job_id=self.job_id,
            job_status="running",
            is_live=True,
            source_type=self.source_type,
            source_fps=0.0,
            processing_fps=0.0,
            frames_acquired=0,
            frames_processed=0,
            dropped_frames=0,
            reconnect_count=0,
            total_volume=0,
            inbound_volume=0,
            outbound_volume=0,
            active_tracks_count=0,
            class_distribution={},
            direction_distribution={},
            lane_occupancies={},
            lane_densities={},
            provenance_tag=self.provenance_category,
            last_frame_timestamp=None,
            last_updated=utcnow(),
        )

    def start(self) -> None:
        """Starts the live analysis execution thread."""
        with self._lock:
            if self._is_running:
                return
            self._is_running = True
            self._stop_requested.clear()
            self._thread = threading.Thread(
                target=self._run_loop,
                name=f"live-analysis-{self.job_id[:8]}",
                daemon=True,
            )
            self._thread.start()
            logger.info("Started LiveAnalysisService for job %s (camera %s)", self.job_id, self.camera_source_id)

    def stop(self) -> None:
        """Signals the live analysis loop to stop and persist."""
        with self._lock:
            if not self._is_running:
                return
            self._stop_requested.set()

    def join(self, timeout: Optional[float] = 5.0) -> None:
        """Waits for the background execution thread to terminate."""
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def is_running(self) -> bool:
        return self._is_running

    def get_latest_preview(self) -> Optional[bytes]:
        """Returns the most recent annotated frame JPEG encoded directly from the live loop."""
        with self._lock:
            return self._latest_preview_jpeg

    def get_snapshot(self) -> Optional[LiveMetricsSnapshot]:
        """Returns the latest in-memory live metrics snapshot."""
        with self._metrics_lock:
            return self._last_snapshot

    def _run_loop(self) -> None:
        """Main CV execution loop."""
        db: Optional[Session] = self._session_factory() if self._session_factory else None
        camera_adapter: Optional[BaseCameraSource] = None
        persisted_session_id: Optional[str] = None

        try:
            # 1. Update job to RUNNING in DB
            if db:
                job = db.query(AnalysisJob).filter(AnalysisJob.id == self.job_id).first()
                if job:
                    job.status = JobStatus.RUNNING.value
                    job.started_at = utcnow()
                    job.updated_at = utcnow()
                    db.commit()

                camera = db.query(CameraSource).filter(CameraSource.id == self.camera_source_id).first()
                if camera:
                    camera.status = CameraSourceStatus.CONNECTING.value
                    camera.updated_at = utcnow()
                    db.commit()

            # 2. Instantiate CV pipeline components
            conf_thresh = self.config.get("confidence_threshold") or settings.default_confidence_threshold
            iou_thresh = self.config.get("iou_threshold") or settings.tracker_iou_threshold
            persistence = self.config.get("persistence_threshold") or 2
            max_fps = self.config.get("processing_fps") or settings.live_max_processing_fps

            detector = YOLOVehicleDetector(confidence_threshold=conf_thresh)
            tracker = ByteTrackVehicleTracker(iou_threshold=iou_thresh)
            tracker.reset()

            # Configure counting line
            cl_config = self.config.get("counting_line")
            if cl_config:
                counting_line = CountingLine(
                    p1=Point2D(x=cl_config["p1"]["x"], y=cl_config["p1"]["y"]),
                    p2=Point2D(x=cl_config["p2"]["x"], y=cl_config["p2"]["y"]),
                    label=cl_config.get("label", "live_tripwire"),
                    direction_a_to_b=cl_config.get("direction_a_to_b", "inbound"),
                    direction_b_to_a=cl_config.get("direction_b_to_a", "outbound"),
                )
            else:
                counting_line = CountingLine.default_from_settings()
            counter = LineCrossingCounter(line=counting_line)

            # Configure lanes
            lanes_config = self.config.get("lanes")
            lane_regions: List[LaneRegion] = []
            if lanes_config:
                lane_regions = [
                    LaneRegion(
                        lane_id=l["lane_id"],
                        name=l["name"],
                        polygon=[(p[0], p[1]) for p in l["polygon"]],
                        direction_hint=l.get("direction_hint"),
                    )
                    for l in lanes_config
                ]
            lane_engine = LaneAssignmentEngine(lane_regions, persistence_threshold=persistence) if lane_regions else None
            metrics_engine = TrafficMetricsEngine()

            # 3. Connect to camera source adapter
            camera_adapter = create_camera_source(
                source_id=self.camera_source_id,
                source_type=self.source_type,
                uri=self.connection_uri,
            )

            connected = camera_adapter.connect()
            if not connected:
                # Attempt bounded reconnect
                for attempt in range(settings.live_reconnect_attempts):
                    if self._stop_requested.is_set():
                        break
                    logger.warning(
                        "Initial camera connect failed for %s. Reconnect attempt %s/%s",
                        self.camera_source_id,
                        attempt + 1,
                        settings.live_reconnect_attempts,
                    )
                    time.sleep(settings.live_reconnect_delay_seconds)
                    if camera_adapter.connect():
                        connected = True
                        break

            if not connected:
                raise AppException(
                    f"Failed to connect to camera source '{self.camera_name}'. Connection refused or source unavailable.",
                    code="camera_connection_failed",
                )

            # Update DB camera status to CONNECTED
            meta = camera_adapter.read_metadata()
            if db:
                camera = db.query(CameraSource).filter(CameraSource.id == self.camera_source_id).first()
                if camera:
                    camera.status = CameraSourceStatus.CONNECTED.value
                    camera.width = meta.width
                    camera.height = meta.height
                    camera.fps = meta.fps
                    camera.last_connected_at = utcnow()
                    camera.updated_at = utcnow()
                    db.commit()

            self._start_time = time.monotonic()
            last_fps_calc_time = self._start_time
            fps_frame_counter = 0
            target_frame_interval = 1.0 / max_fps if max_fps > 0 else 0.2
            last_db_sync_time = self._start_time

            # 4. Processing Loop
            while not self._stop_requested.is_set():
                loop_start = time.monotonic()

                # Read next frame with bounded timeout
                frame_data = camera_adapter.read_frame(timeout_seconds=settings.live_frame_timeout_seconds)

                if frame_data is None:
                    # Potential connection loss or timeout
                    logger.warning("Frame timeout for camera %s; checking connection", self.camera_source_id)
                    if not camera_adapter.is_connected():
                        # Try bounded reconnection
                        reconnected = False
                        for _ in range(settings.live_reconnect_attempts):
                            if self._stop_requested.is_set():
                                break
                            if camera_adapter.reconnect():
                                reconnected = True
                                break
                        if not reconnected:
                            logger.error("Camera %s disconnected and reconnect attempts exhausted", self.camera_source_id)
                            break
                    time.sleep(0.1)
                    continue

                frame_idx, timestamp_sec, frame_bgr = frame_data
                h, w = frame_bgr.shape[:2]

                # Run Detector
                det_res = detector.detect(frame_bgr, frame_index=frame_idx, timestamp_seconds=timestamp_sec)
                self._total_detections += len(det_res)

                # Run Tracker
                active_tracks = tracker.update(
                    detections=det_res,
                    frame_index=frame_idx,
                    timestamp_seconds=timestamp_sec,
                )

                # Run Vehicle Counter
                counter.update(
                    tracked_objects=active_tracks,
                    frame_index=frame_idx,
                    timestamp_seconds=timestamp_sec,
                    frame_width=w,
                    frame_height=h,
                )

                # Run Lane Engine if configured
                lane_occupancies = {}
                lane_densities = {}
                if lane_engine:
                    lane_engine.process_frame(frame_index=frame_idx, tracked_objects=active_tracks)
                    for lr in lane_regions:
                        current_occupancy = len(lane_engine.lane_occupants_history[lr.lane_id][-1]) if lane_engine.lane_occupants_history[lr.lane_id] else 0
                        lane_occupancies[lr.lane_id] = current_occupancy
                        area = lr.area_px2
                        dens = current_occupancy / area if area > 0 else 0.0
                        lane_densities[lr.lane_id] = round(dens, 6)

                self._frames_processed += 1
                fps_frame_counter += 1

                # Calculate moving processing FPS
                now = time.monotonic()
                if (now - last_fps_calc_time) >= 1.0:
                    self._current_processing_fps = round(fps_frame_counter / (now - last_fps_calc_time), 1)
                    fps_frame_counter = 0
                    last_fps_calc_time = now

                # Annotate and encode preview JPEG
                self._generate_preview_jpeg(
                    frame_bgr=frame_bgr,
                    active_tracks=active_tracks,
                    counting_line=counting_line,
                    lane_regions=lane_regions,
                    current_fps=self._current_processing_fps,
                    volume=counter.total_count,
                    inbound=counter.counts_by_direction.get(counting_line.direction_a_to_b, 0),
                    outbound=counter.counts_by_direction.get(counting_line.direction_b_to_a, 0),
                )

                # Update live snapshot
                with self._metrics_lock:
                    self._last_snapshot = LiveMetricsSnapshot(
                        camera_source_id=self.camera_source_id,
                        job_id=self.job_id,
                        job_status="running",
                        is_live=self._is_running,
                        source_type=self.source_type,
                        source_fps=meta.fps,
                        processing_fps=self._current_processing_fps,
                        frames_acquired=camera_adapter.frames_acquired,
                        frames_processed=self._frames_processed,
                        dropped_frames=camera_adapter.dropped_frames,
                        reconnect_count=camera_adapter.reconnect_count,
                        total_volume=counter.total_count,
                        inbound_volume=counter.counts_by_direction.get(counting_line.direction_a_to_b, 0),
                        outbound_volume=counter.counts_by_direction.get(counting_line.direction_b_to_a, 0),
                        active_tracks_count=len([t for t in active_tracks if t.state == TrackState.ACTIVE]),
                        class_distribution=counter.counts_by_class,
                        direction_distribution=counter.counts_by_direction,
                        lane_occupancies=lane_occupancies,
                        lane_densities=lane_densities,
                        provenance_tag=self.provenance_category,
                        last_frame_timestamp=timestamp_sec,
                        last_updated=utcnow(),
                    )

                # Periodic DB sync (every live_metrics_interval_seconds)
                if (now - last_db_sync_time) >= settings.live_metrics_interval_seconds and db:
                    try:
                        j = db.query(AnalysisJob).filter(AnalysisJob.id == self.job_id).first()
                        if j and j.status == JobStatus.RUNNING.value:
                            j.frames_processed = self._frames_processed
                            j.processing_fps = self._current_processing_fps
                            j.updated_at = utcnow()
                            db.commit()

                        c = db.query(CameraSource).filter(CameraSource.id == self.camera_source_id).first()
                        if c:
                            c.last_frame_at = utcnow()
                            c.updated_at = utcnow()
                            db.commit()
                        last_db_sync_time = now
                    except Exception as sync_err:
                        logger.debug("Live metrics DB sync skipped: %s", sync_err)

                # Rate limiting to processing_fps bound
                elapsed = time.monotonic() - loop_start
                sleep_time = target_frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            # 5. Loop Termination & Persistence of Session
            total_duration = time.monotonic() - (self._start_time or time.monotonic())
            observation_sec = max(1.0, round(total_duration, 2))

            logger.info(
                "Live analysis loop finished for job %s: %s frames processed in %.1fs",
                self.job_id,
                self._frames_processed,
                total_duration,
            )

            # Build and persist completed AnalysisSession
            if db:
                session = AnalysisSession(
                    video_id=None,
                    camera_source_id=self.camera_source_id,
                    analysis_type="live_monitoring",
                    session_mode="TEST_FIXTURE" if self.source_type == "test_fixture" else "LIVE_OBSERVATION",
                    status="completed",
                    started_at=utcnow(),
                    completed_at=utcnow(),
                    processing_time_ms=round(total_duration * 1000, 2),
                    total_frames_processed=self._frames_processed,
                    total_vehicles_detected=self._total_detections,
                    total_vehicles_counted=counter.total_count,
                    config_snapshot=self.config,
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                persisted_session_id = session.id

                # Traffic metrics
                counting_output = VideoCountingOutput(
                    video_id=self.camera_source_id,
                    original_filename=self.camera_name,
                    pipeline_stage="live-counting-summary",
                    detector_model=detector.model_name,
                    tracker_name=tracker.tracker_name,
                    counting_line=counting_line,
                    total_frames_processed=self._frames_processed,
                    total_detections_count=self._total_detections,
                    total_unique_tracks=len(counter.counted_track_ids),
                    total_counted_vehicles=counter.total_count,
                    counts_by_class=counter.counts_by_class,
                    counts_by_direction=counter.counts_by_direction,
                    counted_track_ids=counter.counted_track_ids,
                    crossing_events=counter.crossing_events,
                    frames=[],
                    processing_time_ms=round(total_duration * 1000, 2),
                )
                analytics_result = metrics_engine.compute_metrics(
                    counting_output=counting_output,
                    observation_duration_seconds=observation_sec,
                )

                metrics_rec = TrafficMetricsRecord(
                    analysis_session_id=session.id,
                    observation_duration_seconds=analytics_result.observation_duration_seconds,
                    total_volume=analytics_result.total_vehicles,
                    flow_rate_per_minute=analytics_result.flow_rate_per_minute,
                    flow_rate_per_hour=analytics_result.flow_rate_per_hour_extrapolated,
                    is_extrapolated=analytics_result.is_extrapolated,
                    class_distribution=[
                        {"class_name": c.class_name, "count": c.count, "percentage": c.percentage}
                        for c in analytics_result.class_distribution
                    ],
                    direction_distribution=[
                        {"direction": d.direction, "count": d.count, "percentage": d.percentage}
                        for d in analytics_result.directional_distribution
                    ],
                    time_series_buckets=[
                        {
                            "bucket_index": b.bucket_index,
                            "start_time_seconds": b.start_time_seconds,
                            "end_time_seconds": b.end_time_seconds,
                            "vehicle_count": b.vehicle_count,
                            "class_counts": b.class_counts,
                            "inbound_count": b.inbound_count,
                            "outbound_count": b.outbound_count,
                        }
                        for b in analytics_result.time_series
                    ],
                )
                db.add(metrics_rec)

                # Deduplicated crossing events
                seen_crossings = set()
                for ce in counter.crossing_events:
                    key = (ce.track_id, ce.line_label)
                    if key in seen_crossings:
                        continue
                    seen_crossings.add(key)
                    db.add(
                        CrossingEventRecord(
                            analysis_session_id=session.id,
                            track_id=ce.track_id,
                            class_name=ce.class_name,
                            direction=ce.direction,
                            frame_index=ce.frame_index,
                            timestamp_seconds=ce.timestamp_seconds,
                            centroid_x=ce.crossing_point[0] if ce.crossing_point else 0.0,
                            centroid_y=ce.crossing_point[1] if ce.crossing_point else 0.0,
                            line_label=ce.line_label,
                        )
                    )

                # Lane records if any
                if lane_engine:
                    lane_analyzer = LaneAnalyzer(persistence_threshold=persistence)
                    lane_analytics = lane_analyzer.build_result(
                        engine=lane_engine,
                        total_frames_processed=self._frames_processed,
                        video_id=self.camera_source_id,
                        original_filename=self.camera_name,
                    )
                    for ls in lane_analytics.lanes:
                        db.add(
                            LaneResultRecord(
                                analysis_session_id=session.id,
                                lane_id=ls.lane_id,
                                lane_name=ls.lane_name,
                                direction_hint=ls.direction_hint,
                                polygon_json=[list(p) for p in ls.polygon],
                                polygon_area_px2=ls.polygon_area_px2,
                                unique_vehicles_count=ls.total_unique_vehicles,
                                peak_occupancy=ls.peak_occupancy,
                                average_occupancy=ls.average_occupancy,
                                image_space_density=ls.image_space_density_vehicles_per_px2,
                                normalized_density_score=ls.normalized_density_score,
                                vehicle_class_counts=ls.vehicle_class_counts,
                                density_unit=ls.density_unit,
                                density_calibration_warning=lane_analytics.density_calibration_warning,
                            )
                        )

                db.commit()

                # Run anomaly detection hook
                try:
                    from app.services.anomaly.detector import AnomalyDetectionService
                    AnomalyDetectionService().detect_and_persist_for_session(db, session.id)
                except Exception as anom_err:
                    logger.warning("Anomaly detection hook skipped for live session %s: %s", session.id, anom_err)

                # Update job to COMPLETED
                job = db.query(AnalysisJob).filter(AnalysisJob.id == self.job_id).first()
                if job:
                    job.status = JobStatus.COMPLETED.value
                    job.session_id = session.id
                    job.progress = 1.0
                    job.frames_processed = self._frames_processed
                    job.completed_at = utcnow()
                    job.updated_at = utcnow()
                    db.commit()

                # Update camera source to STOPPED
                camera = db.query(CameraSource).filter(CameraSource.id == self.camera_source_id).first()
                if camera:
                    camera.status = CameraSourceStatus.STOPPED.value
                    camera.last_frame_at = utcnow()
                    camera.updated_at = utcnow()
                    db.commit()

        except Exception as err:
            logger.error("Live analysis job %s encountered fatal error: %s", self.job_id, err)
            self._last_error = str(err)
            if db:
                try:
                    db.rollback()
                    job = db.query(AnalysisJob).filter(AnalysisJob.id == self.job_id).first()
                    if job:
                        job.status = JobStatus.FAILED.value
                        job.error_code = "live_analysis_failed"
                        job.error_message = str(err)[:1000]
                        job.completed_at = utcnow()
                        job.updated_at = utcnow()
                        db.commit()

                    camera = db.query(CameraSource).filter(CameraSource.id == self.camera_source_id).first()
                    if camera:
                        camera.status = CameraSourceStatus.ERROR.value
                        camera.last_error = str(err)[:1000]
                        camera.updated_at = utcnow()
                        db.commit()
                except Exception as e:
                    logger.error("Failed persisting live error state: %s", e)

        finally:
            self._is_running = False
            if camera_adapter:
                camera_adapter.release()
            if db:
                db.close()
            logger.info("LiveAnalysisService stopped for job %s", self.job_id)

    def _generate_preview_jpeg(
        self,
        frame_bgr: np.ndarray,
        active_tracks: list,
        counting_line: CountingLine,
        lane_regions: list,
        current_fps: float,
        volume: int,
        inbound: int,
        outbound: int,
    ) -> None:
        """Draws clean HUD, tracks, and lines on frame and updates JPEG buffer."""
        annotated = frame_bgr.copy()
        h, w = annotated.shape[:2]

        # Draw counting tripwire
        p1 = counting_line.p1.to_pixel(w, h)
        p2 = counting_line.p2.to_pixel(w, h)
        cv2.line(annotated, p1, p2, (0, 255, 255), 2)
        cv2.putText(
            annotated,
            f"Tripwire: {counting_line.label}",
            (min(p1[0], p2[0]) + 10, max(15, min(p1[1], p2[1]) - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            (0, 255, 255),
            1,
            cv2.LINE_AA,
        )

        # Draw lane polygons
        for lr in lane_regions:
            pts = np.array(lr.polygon, np.int32).reshape((-1, 1, 2))
            cv2.polylines(annotated, [pts], True, (255, 128, 0), 1)

        # Draw active vehicle tracks
        for obj in active_tracks:
            if obj.state == TrackState.TERMINATED:
                continue
            box = obj.bbox
            x1, y1, x2, y2 = int(box.x1), int(box.y1), int(box.x2), int(box.y2)

            color = (0, 230, 0) if obj.state == TrackState.ACTIVE else (0, 165, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            label = f"#{obj.track_id} {obj.class_name}"
            cv2.rectangle(annotated, (x1, max(0, y1 - 18)), (x1 + len(label) * 8 + 8, y1), color, -1)
            cv2.putText(
                annotated,
                label,
                (x1 + 4, max(12, y1 - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (0, 0, 0),
                1,
                cv2.LINE_AA,
            )

        # Draw live monitoring HUD overlay (top left)
        cv2.rectangle(annotated, (10, 10), (280, 85), (20, 20, 20), -1)
        cv2.rectangle(annotated, (10, 10), (280, 85), (60, 60, 60), 1)

        hud_lines = [
            f"LIVE STREAM: {self.camera_name[:20]}",
            f"FPS: {current_fps:.1f} | Active Tracks: {len([t for t in active_tracks if t.state == TrackState.ACTIVE])}",
            f"Vol: {volume} (In: {inbound}, Out: {outbound})",
            f"Provenance: {self.provenance_category.upper()}",
        ]
        for idx, line in enumerate(hud_lines):
            color = (0, 255, 200) if idx == 0 else (220, 220, 220)
            cv2.putText(
                annotated,
                line,
                (18, 28 + idx * 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.38,
                color,
                1,
                cv2.LINE_AA,
            )

        # Encode JPEG
        ret, buf = cv2.imencode(".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ret:
            with self._lock:
                self._latest_preview_jpeg = buf.tobytes()

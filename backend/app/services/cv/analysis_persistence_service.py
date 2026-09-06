"""
Analysis Persistence Service.
Phase 10: Database Integration.

Orchestrates running the verified CV pipeline stages (VideoSource -> Detector -> Tracker ->
Counter -> TrafficMetricsEngine -> LaneAnalyzer) and atomically persisting structured
sessions, flow metrics, lane density results, and crossing events to PostgreSQL/SQLite.
"""
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.models.analysis import (
    AnalysisSession,
    CrossingEventRecord,
    LaneResultRecord,
    TrafficMetricsRecord,
)
from app.models.video import Video
from app.schemas.analysis import (
    AnalysisRunRequest,
    AnalysisSessionDetailResponse,
    AnalysisSessionSummarySchema,
    CrossingEventSchema,
    LaneResultRecordSchema,
    TrafficMetricsRecordSchema,
)
from app.services.cv.detector import Detector, YOLOVehicleDetector
from app.services.cv.lane_analyzer import LaneAnalyzer, LaneRegion
from app.services.cv.tracker import ByteTrackVehicleTracker, Tracker
from app.services.cv.traffic_metrics_engine import TrafficMetricsEngine
from app.services.cv.vehicle_counter import (
    CountingLine,
    LineCrossingCounter,
    Point2D,
    VehicleCounter,
    VideoCountingOutput,
)
from app.services.cv.video_source import VideoSource

logger = get_logger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)



class AnalysisPersistenceService:
    """
    Coordinates end-to-end video analysis execution and atomic database persistence.
    """

    def __init__(
        self,
        default_detector: Optional[Detector] = None,
        default_tracker: Optional[Tracker] = None,
        default_counter: Optional[VehicleCounter] = None,
        default_metrics_engine: Optional[TrafficMetricsEngine] = None,
        default_lane_analyzer: Optional[LaneAnalyzer] = None,
    ):
        self._detector = default_detector or YOLOVehicleDetector()
        self._tracker = default_tracker or ByteTrackVehicleTracker()
        self._counter = default_counter or LineCrossingCounter()
        self._metrics_engine = default_metrics_engine or TrafficMetricsEngine()
        self._lane_analyzer = default_lane_analyzer or LaneAnalyzer(persistence_threshold=2)

    def execute_and_persist(
        self,
        video: Video,
        db: Session,
        request: AnalysisRunRequest,
    ) -> AnalysisSession:
        """
        Executes the CV pipeline on the specified video and persists all results atomically.
        """
        storage_path = Path(video.storage_path)
        if not storage_path.exists():
            raise AppException(
                f"Underlying video file '{video.original_filename}' is missing from server storage.",
                code="file_not_found",
                status_code=404,
            )

        # 1. Resolve configuration parameters
        conf_thresh = request.confidence_threshold or self._detector.confidence_threshold
        proc_fps = request.processing_fps or settings.processing_fps
        max_frames = request.max_frames or 100
        iou_thresh = request.iou_threshold or self._tracker.iou_threshold
        persistence = request.persistence_threshold or 2

        # Configure counting line
        counting_line: CountingLine
        if request.counting_line:
            counting_line = CountingLine(
                p1=Point2D(x=request.counting_line.p1.x, y=request.counting_line.p1.y),
                p2=Point2D(x=request.counting_line.p2.x, y=request.counting_line.p2.y),
                label=request.counting_line.label or "main_line",
                direction_a_to_b=request.counting_line.direction_a_to_b or "inbound",
                direction_b_to_a=request.counting_line.direction_b_to_a or "outbound",
            )
        else:
            counting_line = CountingLine.default_from_settings()

        # Configure lane polygons
        lane_regions: List[LaneRegion] = []
        if request.lanes:
            lane_regions = [
                LaneRegion(
                    lane_id=l.lane_id,
                    name=l.name,
                    polygon=[(float(p[0]), float(p[1])) for p in l.polygon],
                    direction_hint=l.direction_hint,
                )
                for l in request.lanes
            ]
        elif request.analysis_type in ("full_pipeline", "lane_analysis"):
            # Default dual-lane split if not provided
            lane_regions = [
                LaneRegion(
                    lane_id="lane_left",
                    name="Left Traffic Lane",
                    polygon=[(0.0, 0.0), (320.0, 0.0), (320.0, 480.0), (0.0, 480.0)],
                    direction_hint="inbound",
                ),
                LaneRegion(
                    lane_id="lane_right",
                    name="Right Traffic Lane",
                    polygon=[(320.0, 0.0), (640.0, 0.0), (640.0, 480.0), (320.0, 480.0)],
                    direction_hint="outbound",
                ),
            ]

        # Config snapshot for reproducibility (ARCHITECTURE.md §8)
        config_snapshot: Dict[str, Any] = {
            "analysis_type": request.analysis_type,
            "confidence_threshold": conf_thresh,
            "processing_fps": proc_fps,
            "max_frames": max_frames,
            "iou_threshold": iou_thresh,
            "persistence_threshold": persistence,
            "counting_line": {
                "p1": {"x": counting_line.p1.x, "y": counting_line.p1.y},
                "p2": {"x": counting_line.p2.x, "y": counting_line.p2.y},
                "label": counting_line.label,
                "direction_a_to_b": counting_line.direction_a_to_b,
                "direction_b_to_a": counting_line.direction_b_to_a,
            },
            "lanes": [
                {
                    "lane_id": lr.lane_id,
                    "name": lr.name,
                    "polygon": lr.polygon,
                    "direction_hint": lr.direction_hint,
                }
                for lr in lane_regions
            ],
        }

        # 2. Create and persist initial AnalysisSession record
        session = AnalysisSession(
            video_id=video.id,
            analysis_type=request.analysis_type,
            status="processing",
            started_at=utcnow(),
            config_snapshot=config_snapshot,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        # 3. Instantiate pipeline stages
        detector = (
            self._detector
            if conf_thresh == self._detector.confidence_threshold
            else YOLOVehicleDetector(confidence_threshold=conf_thresh)
        )
        tracker = (
            self._tracker
            if iou_thresh == self._tracker.iou_threshold
            else ByteTrackVehicleTracker(iou_threshold=iou_thresh)
        )
        tracker.reset()
        counter = LineCrossingCounter(line=counting_line)
        lane_analyzer = LaneAnalyzer(persistence_threshold=persistence)

        start_time = time.perf_counter()
        try:
            # 4. Run VideoSource through CV Pipeline
            with VideoSource(storage_path) as source:
                meta = source.read_metadata()
                w, h = meta.width, meta.height

                # Stage 1 & 2: Detection + Tracking
                tracking_output = tracker.track_video(
                    video_source=source,
                    detector=detector,
                    max_frames=max_frames,
                    target_fps=proc_fps,
                )

                # Stage 3: Virtual Line Crossing Counting
                counter.reset()
                for frame_result in tracking_output.frames:
                    counter.update(
                        tracked_objects=frame_result.tracked_objects,
                        frame_index=frame_result.frame_index,
                        timestamp_seconds=frame_result.timestamp_seconds,
                        frame_width=w,
                        frame_height=h,
                    )

                duration = (
                    tracking_output.frames[-1].timestamp_seconds
                    if tracking_output.frames
                    else 0.0
                )
                if duration <= 0.0 and tracking_output.total_frames_processed > 0:
                    duration = tracking_output.total_frames_processed / proc_fps

                counting_output = VideoCountingOutput(
                    video_id=video.id,
                    original_filename=video.original_filename,
                    pipeline_stage="counting-run",
                    detector_model=detector.model_name,
                    tracker_name=tracker.tracker_name,
                    counting_line=counting_line,
                    total_frames_processed=tracking_output.total_frames_processed,
                    total_detections_count=tracking_output.total_detections_count,
                    total_unique_tracks=tracking_output.total_unique_tracks,
                    total_counted_vehicles=counter.total_count,
                    counts_by_class=counter.counts_by_class,
                    counts_by_direction=counter.counts_by_direction,
                    counted_track_ids=counter.counted_track_ids,
                    crossing_events=counter.crossing_events,
                    frames=[],
                    processing_time_ms=tracking_output.processing_time_ms,
                )

                # Stage 4: Traffic Flow Analytics
                analytics_result = self._metrics_engine.compute_metrics(
                    counting_output=counting_output,
                    observation_duration_seconds=duration,
                )

                # Stage 5: Lane Analysis & Density Estimation
                lane_result = None
                if lane_regions:
                    lane_result = lane_analyzer.analyze(
                        tracking_output=tracking_output,
                        lanes=lane_regions,
                        video_id=video.id,
                        original_filename=video.original_filename,
                    )

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # 5. Persist Child Records in an Atomic Transaction
            session.status = "completed"
            session.completed_at = utcnow()
            session.processing_time_ms = round(elapsed_ms, 2)
            session.total_frames_processed = tracking_output.total_frames_processed
            session.total_vehicles_detected = tracking_output.total_detections_count
            session.total_vehicles_counted = counting_output.total_counted_vehicles

            # Persist Traffic Metrics
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

            # Persist Lane Results
            if lane_result:
                for lane_summary in lane_result.lanes:
                    lane_rec = LaneResultRecord(
                        analysis_session_id=session.id,
                        lane_id=lane_summary.lane_id,
                        lane_name=lane_summary.lane_name,
                        direction_hint=lane_summary.direction_hint,
                        polygon_json=[list(p) for p in lane_summary.polygon],
                        polygon_area_px2=lane_summary.polygon_area_px2,
                        unique_vehicles_count=lane_summary.total_unique_vehicles,
                        peak_occupancy=lane_summary.peak_occupancy,
                        average_occupancy=lane_summary.average_occupancy,
                        image_space_density=lane_summary.image_space_density_vehicles_per_px2,
                        normalized_density_score=lane_summary.normalized_density_score,
                        vehicle_class_counts=lane_summary.vehicle_class_counts,
                        density_unit=lane_summary.density_unit,
                        density_calibration_warning=lane_result.density_calibration_warning,
                    )
                    db.add(lane_rec)

            # Persist Crossing Events (Deduplicated)
            seen_tracks = set()
            for event in counting_output.crossing_events:
                event_key = (event.track_id, event.line_label)
                if event_key in seen_tracks:
                    continue
                seen_tracks.add(event_key)

                event_rec = CrossingEventRecord(
                    analysis_session_id=session.id,
                    track_id=event.track_id,
                    class_name=event.class_name,
                    direction=event.direction,
                    frame_index=event.frame_index,
                    timestamp_seconds=event.timestamp_seconds,
                    centroid_x=event.crossing_point[0] if event.crossing_point else 0.0,
                    centroid_y=event.crossing_point[1] if event.crossing_point else 0.0,
                    line_label=event.line_label,
                )
                db.add(event_rec)

            db.commit()
            db.refresh(session)
            logger.info(
                "Persisted AnalysisSession %s for video %s: %s vehicles counted, %s frames in %.1fms",
                session.id,
                video.id,
                session.total_vehicles_counted,
                session.total_frames_processed,
                elapsed_ms,
            )
            return session

        except Exception as err:
            db.rollback()
            session.status = "failed"
            session.completed_at = utcnow()
            session.error_message = str(err)[:1000]
            try:
                db.commit()
            except Exception as commit_err:
                logger.error("Failed to commit session failure status: %s", commit_err)
            logger.error("Analysis execution failed for video %s (Session %s): %s", video.id, session.id, err)
            raise

    @staticmethod
    def session_to_detail_response(session: AnalysisSession) -> AnalysisSessionDetailResponse:
        """Converts an AnalysisSession ORM model instance into a structured detail response."""
        traffic_metrics_schema = None
        if session.traffic_metrics:
            tm = session.traffic_metrics
            traffic_metrics_schema = TrafficMetricsRecordSchema(
                id=tm.id,
                observation_duration_seconds=tm.observation_duration_seconds,
                total_volume=tm.total_volume,
                flow_rate_per_minute=tm.flow_rate_per_minute,
                flow_rate_per_hour=tm.flow_rate_per_hour,
                is_extrapolated=tm.is_extrapolated,
                class_distribution=tm.class_distribution,
                direction_distribution=tm.direction_distribution,
                time_series_buckets=tm.time_series_buckets,
                created_at=tm.created_at,
            )

        lane_results_schemas = [
            LaneResultRecordSchema(
                id=lr.id,
                lane_id=lr.lane_id,
                lane_name=lr.lane_name,
                direction_hint=lr.direction_hint,
                polygon_json=lr.polygon_json,
                polygon_area_px2=lr.polygon_area_px2,
                unique_vehicles_count=lr.unique_vehicles_count,
                peak_occupancy=lr.peak_occupancy,
                average_occupancy=lr.average_occupancy,
                image_space_density=lr.image_space_density,
                normalized_density_score=lr.normalized_density_score,
                vehicle_class_counts=lr.vehicle_class_counts,
                density_unit=lr.density_unit,
                density_calibration_warning=lr.density_calibration_warning,
                created_at=lr.created_at,
            )
            for lr in (session.lane_results or [])
        ]

        crossing_events_schemas = [
            CrossingEventSchema(
                id=ce.id,
                track_id=ce.track_id,
                class_name=ce.class_name,
                direction=ce.direction,
                frame_index=ce.frame_index,
                timestamp_seconds=ce.timestamp_seconds,
                centroid_x=ce.centroid_x,
                centroid_y=ce.centroid_y,
                line_label=ce.line_label,
                created_at=ce.created_at,
            )
            for ce in (session.crossing_events or [])
        ]

        video_filename = session.video.original_filename if session.video else None

        return AnalysisSessionDetailResponse(
            id=session.id,
            video_id=session.video_id,
            video_filename=video_filename,
            analysis_type=session.analysis_type,
            status=session.status,
            started_at=session.started_at,
            completed_at=session.completed_at,
            processing_time_ms=session.processing_time_ms,
            total_frames_processed=session.total_frames_processed,
            total_vehicles_detected=session.total_vehicles_detected,
            total_vehicles_counted=session.total_vehicles_counted,
            config_snapshot=session.config_snapshot,
            error_message=session.error_message,
            traffic_metrics=traffic_metrics_schema,
            lane_results=lane_results_schemas,
            crossing_events=crossing_events_schemas,
        )

    @staticmethod
    def session_to_summary_schema(session: AnalysisSession) -> AnalysisSessionSummarySchema:
        """Converts an AnalysisSession ORM model instance into a summary schema."""
        video_filename = session.video.original_filename if session.video else None
        return AnalysisSessionSummarySchema(
            id=session.id,
            video_id=session.video_id,
            video_filename=video_filename,
            analysis_type=session.analysis_type,
            status=session.status,
            started_at=session.started_at,
            completed_at=session.completed_at,
            processing_time_ms=session.processing_time_ms,
            total_frames_processed=session.total_frames_processed,
            total_vehicles_detected=session.total_vehicles_detected,
            total_vehicles_counted=session.total_vehicles_counted,
            error_message=session.error_message,
        )


_global_persistence_service: Optional[AnalysisPersistenceService] = None


def get_analysis_persistence_service() -> AnalysisPersistenceService:
    """Returns a module singleton AnalysisPersistenceService instance."""
    global _global_persistence_service
    if _global_persistence_service is None:
        _global_persistence_service = AnalysisPersistenceService()
    return _global_persistence_service

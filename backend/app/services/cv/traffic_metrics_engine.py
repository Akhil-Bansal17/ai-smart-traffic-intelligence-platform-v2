"""
Traffic Analytics & Flow Metrics Engine.

Architecture:
    TrackedObject / Counting Events -> TrafficMetricsEngine -> TrafficMetricsResult -> API / UI

Strict Phase 8 boundaries:
- Operates on real tracked vehicles and Phase 7 counting output.
- Computes mathematically grounded flow rates, class distributions, and directional balance.
- Generates transparent, non-fabricated time-series volume bucketing.
- Clear labeling for any extrapolated metrics (e.g. hourly flow from short clips).
- NO lane detection (Phase 8/9), NO congestion prediction, NO ML forecasting.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import math
import time
from typing import Dict, List, Optional, Tuple

from app.config.settings import settings
from app.core.logging import get_logger
from app.services.cv.detector import Detector, YOLOVehicleDetector
from app.services.cv.tracker import ByteTrackVehicleTracker, Tracker
from app.services.cv.vehicle_counter import (
    CountingLine,
    CrossingEvent,
    LineCrossingCounter,
    VehicleCounter,
    VideoCountingOutput,
)
from app.services.cv.video_source import VideoSource

logger = get_logger(__name__)


@dataclass
class ClassMetric:
    """Vehicle class volume count and percentage breakdown."""
    class_name: str
    count: int
    percentage: float


@dataclass
class DirectionMetric:
    """Directional volume count and percentage breakdown."""
    direction: str
    count: int
    percentage: float


@dataclass
class TimeSeriesBucket:
    """Volume and class aggregation within a discrete time window."""
    bucket_index: int
    start_time_seconds: float
    end_time_seconds: float
    vehicle_count: int
    class_counts: Dict[str, int] = field(default_factory=dict)
    inbound_count: int = 0
    outbound_count: int = 0


@dataclass
class TrafficMetricsResult:
    """Comprehensive traffic flow analytics and metrics output."""
    video_id: Optional[str]
    original_filename: Optional[str]
    pipeline_stage: str = "analytics-run"
    observation_duration_seconds: float = 0.0
    total_vehicles: int = 0
    flow_rate_per_minute: float = 0.0
    flow_rate_per_hour_extrapolated: float = 0.0
    is_extrapolated: bool = True
    inbound_count: int = 0
    outbound_count: int = 0
    inbound_percentage: float = 0.0
    outbound_percentage: float = 0.0
    class_distribution: List[ClassMetric] = field(default_factory=list)
    directional_distribution: List[DirectionMetric] = field(default_factory=list)
    time_series: List[TimeSeriesBucket] = field(default_factory=list)
    total_frames_processed: int = 0
    total_detections: int = 0
    unique_tracks: int = 0
    counting_line_label: str = "main_tripwire"
    processing_time_ms: float = 0.0
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TrafficMetricsEngine:
    """
    Computes mathematically rigorous traffic analytics from tracking and counting events.
    Guarantees division-by-zero safety, transparent extrapolation labeling, and strict data honesty.
    """

    def __init__(self, default_bucket_seconds: float = 5.0):
        self.default_bucket_seconds = max(0.5, float(default_bucket_seconds))

    @staticmethod
    def calculate_class_distribution(
        counts_by_class: Dict[str, int],
        total_count: int,
    ) -> List[ClassMetric]:
        """
        Calculates count and percentage per vehicle class.
        Safe against zero total vehicles.
        """
        metrics: List[ClassMetric] = []
        for cls_name, count in sorted(counts_by_class.items()):
            pct = (count / total_count * 100.0) if total_count > 0 else 0.0
            metrics.append(
                ClassMetric(
                    class_name=cls_name,
                    count=count,
                    percentage=round(pct, 2),
                )
            )
        return metrics

    @staticmethod
    def calculate_directional_distribution(
        counts_by_direction: Dict[str, int],
        total_count: int,
    ) -> List[DirectionMetric]:
        """
        Calculates count and percentage per crossing direction.
        Safe against zero total vehicles.
        """
        metrics: List[DirectionMetric] = []
        for direction, count in sorted(counts_by_direction.items()):
            pct = (count / total_count * 100.0) if total_count > 0 else 0.0
            metrics.append(
                DirectionMetric(
                    direction=direction,
                    count=count,
                    percentage=round(pct, 2),
                )
            )
        return metrics

    @staticmethod
    def calculate_flow_rates(
        total_count: int,
        observation_duration_seconds: float,
    ) -> Tuple[float, float]:
        """
        Computes flow rate per minute and extrapolated flow rate per hour:
        - flow_per_minute = total_count / (duration_sec / 60.0)
        - flow_per_hour = total_count / (duration_sec / 3600.0)
        Returns (0.0, 0.0) if duration <= 0.
        """
        if observation_duration_seconds <= 0.0 or total_count == 0:
            return (0.0, 0.0)

        per_minute = total_count / (observation_duration_seconds / 60.0)
        per_hour = total_count / (observation_duration_seconds / 3600.0)

        return (round(per_minute, 2), round(per_hour, 2))

    @staticmethod
    def generate_time_series_buckets(
        crossing_events: List[CrossingEvent],
        total_duration_seconds: float,
        bucket_seconds: float = 5.0,
        max_buckets: int = 500,
    ) -> List[TimeSeriesBucket]:
        """
        Assigns real crossing events to discrete time intervals [start, end).
        Never manufactures synthetic curves or interpolated points.
        """
        if total_duration_seconds <= 0.0:
            return []

        bucket_width = max(0.5, float(bucket_seconds))
        raw_num_buckets = math.ceil(total_duration_seconds / bucket_width)
        num_buckets = min(raw_num_buckets, max_buckets)

        # Initialize discrete buckets
        buckets: List[TimeSeriesBucket] = [
            TimeSeriesBucket(
                bucket_index=i,
                start_time_seconds=round(i * bucket_width, 2),
                end_time_seconds=round(min(total_duration_seconds, (i + 1) * bucket_width), 2),
                vehicle_count=0,
                class_counts={},
                inbound_count=0,
                outbound_count=0,
            )
            for i in range(num_buckets)
        ]

        for event in crossing_events:
            t = max(0.0, float(event.timestamp_seconds))
            b_idx = int(t // bucket_width)

            # Clamp index to last bucket if event is at video boundary
            if b_idx >= num_buckets:
                b_idx = num_buckets - 1

            if 0 <= b_idx < len(buckets):
                bucket = buckets[b_idx]
                bucket.vehicle_count += 1
                bucket.class_counts[event.class_name] = bucket.class_counts.get(event.class_name, 0) + 1
                if event.direction.lower() == "inbound":
                    bucket.inbound_count += 1
                elif event.direction.lower() == "outbound":
                    bucket.outbound_count += 1

        return buckets

    def compute_metrics(
        self,
        counting_output: VideoCountingOutput,
        observation_duration_seconds: float,
        time_bucket_seconds: Optional[float] = None,
    ) -> TrafficMetricsResult:
        """
        Transforms counting output into full TrafficMetricsResult.
        """
        duration = max(0.0, float(observation_duration_seconds))
        total_vol = counting_output.total_counted_vehicles
        bucket_sec = time_bucket_seconds or self.default_bucket_seconds

        # 1. Flow Rates
        flow_min, flow_hour = self.calculate_flow_rates(total_vol, duration)

        # 2. Class Distribution
        class_dist = self.calculate_class_distribution(
            counting_output.counts_by_class, total_vol
        )

        # 3. Directional Distribution
        dir_dist = self.calculate_directional_distribution(
            counting_output.counts_by_direction, total_vol
        )

        inbound_cnt = counting_output.counts_by_direction.get("inbound", 0)
        outbound_cnt = counting_output.counts_by_direction.get("outbound", 0)
        inbound_pct = round((inbound_cnt / total_vol * 100.0), 2) if total_vol > 0 else 0.0
        outbound_pct = round((outbound_cnt / total_vol * 100.0), 2) if total_vol > 0 else 0.0

        # 4. Time Series Bucketing
        time_series = self.generate_time_series_buckets(
            crossing_events=counting_output.crossing_events,
            total_duration_seconds=duration,
            bucket_seconds=bucket_sec,
        )

        return TrafficMetricsResult(
            video_id=counting_output.video_id,
            original_filename=counting_output.original_filename,
            pipeline_stage="analytics-run",
            observation_duration_seconds=round(duration, 2),
            total_vehicles=total_vol,
            flow_rate_per_minute=flow_min,
            flow_rate_per_hour_extrapolated=flow_hour,
            is_extrapolated=(duration < 3600.0),
            inbound_count=inbound_cnt,
            outbound_count=outbound_cnt,
            inbound_percentage=inbound_pct,
            outbound_percentage=outbound_pct,
            class_distribution=class_dist,
            directional_distribution=dir_dist,
            time_series=time_series,
            total_frames_processed=counting_output.total_frames_processed,
            total_detections=counting_output.total_detections_count,
            unique_tracks=counting_output.total_unique_tracks,
            counting_line_label=counting_output.counting_line.label,
            processing_time_ms=counting_output.processing_time_ms,
        )

    def analyze_video(
        self,
        video_source: VideoSource,
        detector: Detector,
        tracker: Tracker,
        counter: VehicleCounter,
        max_frames: Optional[int] = None,
        target_fps: Optional[int] = None,
        time_bucket_seconds: Optional[float] = None,
        video_id: Optional[str] = None,
        original_filename: Optional[str] = None,
    ) -> TrafficMetricsResult:
        """
        Executes end-to-end analytics pipeline:
        VideoSource -> Detector -> Tracker -> Counter -> TrafficMetricsEngine.
        """
        t0 = time.perf_counter()

        fps = target_fps or settings.processing_fps
        effective_max_frames = min(max_frames if max_frames is not None else 50, 300)

        # 1. Run counting pipeline
        if hasattr(counter, "count_video"):
            counting_output = counter.count_video(
                video_source=video_source,
                detector=detector,
                tracker=tracker,
                max_frames=effective_max_frames,
                target_fps=fps,
                video_id=video_id,
                original_filename=original_filename,
            )
        else:
            raise ValueError("Provided counter does not implement count_video")

        # 2. Compute observation duration from processed frames
        obs_duration = (
            counting_output.total_frames_processed / fps
            if fps > 0
            else 0.0
        )

        # 3. Compute analytics metrics
        metrics = self.compute_metrics(
            counting_output=counting_output,
            observation_duration_seconds=obs_duration,
            time_bucket_seconds=time_bucket_seconds,
        )

        total_elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        metrics.processing_time_ms = total_elapsed_ms

        logger.info(
            "Computed traffic analytics for video %s: %d vehicles, %.1f veh/min, %.1fs observation in %.1fms",
            video_id,
            metrics.total_vehicles,
            metrics.flow_rate_per_minute,
            metrics.observation_duration_seconds,
            metrics.processing_time_ms,
        )

        return metrics

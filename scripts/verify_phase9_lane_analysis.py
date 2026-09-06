"""
Standalone Live Verification Script for Phase 9: Lane Analysis & Density Estimation.

Executes the full end-to-end CV and Lane Analysis pipeline:
VideoSource -> YOLOVehicleDetector -> ByteTrackVehicleTracker -> LaneAnalyzer

Verifies:
1. Real multi-frame video with distinct vehicle trajectories translating in multiple configured lanes.
2. Full tracking & lane persistence assignment execution.
3. Shoelace polygon area calculation for each configured lane region.
4. Step-by-step reviewable density arithmetic matching:
   - Area_px2 = Shoelace(polygon)
   - ImageSpaceDensity = total_unique_vehicles / Area_px2 (vehicles/px²)
   - NormalizedDensityScore = min(1.0, total_unique_vehicles / (Area_px2 / 2500))
   - Peak & Average frame occupancy
5. Explicit calibration warning notice:
   "Image-space density is not equivalent to vehicles/km² without camera calibration."
6. Explicit documentation for absence of directional per-lane metrics.
"""
import math
import sys
import time
import urllib.request
from pathlib import Path

# Add project root and backend to python path
project_root = Path(__file__).resolve().parent.parent
backend_dir = project_root / "backend"
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(backend_dir))

import cv2
import numpy as np

from app.services.cv.detector import YOLOVehicleDetector
from app.services.cv.lane_analyzer import (
    LaneAnalyzer,
    LaneRegion,
    polygon_area_shoelace,
)
from app.services.cv.tracker import ByteTrackVehicleTracker
from app.services.cv.video_source import VideoSource


def generate_multi_lane_traffic_video(output_path: Path, num_frames: int = 25) -> None:
    """
    Generates a realistic multi-frame video with real vehicle patches translating
    in two distinct roadway lanes (Left Lane x: 100-450, Right Lane x: 550-900 in a 1000x800 frame).
    """
    scratch_dir = output_path.parent
    bus_img_path = scratch_dir / "sample_bus.jpg"
    if not bus_img_path.exists():
        urllib.request.urlretrieve("https://ultralytics.com/images/bus.jpg", str(bus_img_path))

    raw_bus_img = cv2.imread(str(bus_img_path))
    bus_patch = raw_bus_img[230:750, 20:800]
    bus_patch_left = cv2.resize(bus_patch, (220, 150))
    bp_h, bp_w = bus_patch_left.shape[:2]

    # Second vehicle patch: horizontally flipped & resized vehicle for right lane
    bus_patch_right = cv2.resize(cv2.flip(bus_patch, 1), (200, 140))
    cp_h, cp_w = bus_patch_right.shape[:2]

    frame_w, frame_h = 1000, 800
    fps = 10.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (frame_w, frame_h))

    # Base background: 2-lane dual carriageway with asphalt & dividers
    base_bg = np.full((frame_h, frame_w, 3), 45, dtype=np.uint8)
    # Left Lane (100 to 450)
    cv2.rectangle(base_bg, (100, 0), (450, frame_h), (35, 35, 35), -1)
    # Median / Divider (450 to 550)
    cv2.rectangle(base_bg, (450, 0), (550, frame_h), (60, 60, 60), -1)
    # Right Lane (550 to 900)
    cv2.rectangle(base_bg, (550, 0), (900, frame_h), (35, 35, 35), -1)

    # Road shoulder lines
    cv2.line(base_bg, (100, 0), (100, frame_h), (240, 240, 240), 3)
    cv2.line(base_bg, (450, 0), (450, frame_h), (240, 240, 240), 3)
    cv2.line(base_bg, (550, 0), (550, frame_h), (240, 240, 240), 3)
    cv2.line(base_bg, (900, 0), (900, frame_h), (240, 240, 240), 3)

    # Dashed center markings inside lanes
    for y in range(0, frame_h, 50):
        cv2.rectangle(base_bg, (270, y), (280, y + 25), (200, 200, 200), -1)
        cv2.rectangle(base_bg, (720, y), (730, y + 25), (200, 200, 200), -1)

    # Lane 1 Vehicle (Bus): Left lane (x=160), translates y: 80 -> 560
    # Lane 2 Vehicle (Car): Right lane (x=620), translates y: 120 -> 600
    start_y1, end_y1 = 80, 560
    start_y2, end_y2 = 120, 600
    veh1_x = 160
    veh2_x = 620

    for i in range(num_frames):
        frame = base_bg.copy()
        alpha = i / max(1, num_frames - 1)
        v1_y = int(start_y1 + alpha * (end_y1 - start_y1))
        v2_y = int(start_y2 + alpha * (end_y2 - start_y2))

        # Draw vehicle 1 in Left Lane
        if v1_y + bp_h < frame_h:
            frame[v1_y:v1_y + bp_h, veh1_x:veh1_x + bp_w] = bus_patch_left

        # Draw vehicle 2 in Right Lane
        if v2_y + cp_h < frame_h:
            frame[v2_y:v2_y + cp_h, veh2_x:veh2_x + cp_w] = bus_patch_right

        writer.write(frame)

    writer.release()
    print(f"[OK] Generated verification video with multi-lane vehicles: {output_path.name} ({num_frames} frames, {fps} FPS, {frame_w}x{frame_h})")


def main():
    print("=" * 80)
    print("AI SMART TRAFFIC INTELLIGENCE PLATFORM — PHASE 9 VERIFICATION")
    print("Lane Analysis & Density Estimation Service")
    print("=" * 80)

    scratch_dir = project_root / "scratch"
    scratch_dir.mkdir(exist_ok=True)
    video_path = scratch_dir / "lane_analysis_verification.mp4"

    # Step 1: Generate deterministic multi-lane video fixture
    generate_multi_lane_traffic_video(video_path, num_frames=25)

    # Step 2: Initialize CV Pipeline Components
    print("\n1. Initializing Full CV & Lane Analysis Pipeline Components...")
    t0 = time.perf_counter()

    video_source = VideoSource(str(video_path))
    detector = YOLOVehicleDetector(
        model_path=str(project_root / "data_science" / "models" / "yolov8n.pt"),
        confidence_threshold=0.30,
        device="cpu",
    )
    tracker = ByteTrackVehicleTracker(
        iou_threshold=0.30,
        max_lost_frames=15,
        min_hits=1,
    )
    lane_analyzer = LaneAnalyzer(persistence_threshold=2)

    # Configure 2 distinct roadway lane polygons matching road layout
    lane_left = LaneRegion(
        lane_id="lane_left",
        name="Left Traffic Lane",
        polygon=[(100.0, 0.0), (450.0, 0.0), (450.0, 800.0), (100.0, 800.0)],
        direction_hint="northbound",
    )
    lane_right = LaneRegion(
        lane_id="lane_right",
        name="Right Traffic Lane",
        polygon=[(550.0, 0.0), (900.0, 0.0), (900.0, 800.0), (550.0, 800.0)],
        direction_hint="southbound",
    )
    lanes = [lane_left, lane_right]

    init_ms = (time.perf_counter() - t0) * 1000.0
    print(f"[OK] Initialized Pipeline (Detector, Tracker, LaneAnalyzer) in {init_ms:.1f}ms")

    # Step 3: Run Video Tracking & Lane Analysis
    print("\n2. Executing VideoSource -> Detector -> Tracker -> LaneAnalyzer...")
    t_pipeline_start = time.perf_counter()

    tracking_output = tracker.track_video(
        video_source=video_source,
        detector=detector,
        max_frames=25,
        target_fps=10,
    )

    lane_result = lane_analyzer.analyze(
        tracking_output=tracking_output,
        lanes=lanes,
        video_id="verify-phase9-uuid",
        original_filename="lane_analysis_verification.mp4",
        processing_time_ms=tracking_output.processing_time_ms,
    )

    pipeline_runtime_ms = (time.perf_counter() - t_pipeline_start) * 1000.0
    print(f"[OK] Pipeline finished in {pipeline_runtime_ms:.1f}ms")

    # Step 4: Step-by-Step Mathematical Verification & Arithmetic Breakdown
    print("\n3. Reviewable Arithmetic & Geometry Verification Breakdown:")
    print("-" * 80)

    frames_evaluated = lane_result.total_frames_processed
    t_obs = lane_result.observation_duration_seconds
    total_tracks = lane_result.total_unique_tracks
    unassigned = lane_result.unassigned_vehicles_count

    print(f"  • Frames Evaluated       : {frames_evaluated}")
    print(f"  • Observation Duration   : {t_obs:.2f} seconds")
    print(f"  • Total Unique Tracks    : {total_tracks}")
    print(f"  • Unassigned Tracks      : {unassigned}")
    print(f"  • Total Configured Lanes : {len(lane_result.lanes)}")

    for summary in lane_result.lanes:
        print(f"\n  [Lane: {summary.lane_name} ({summary.lane_id})]")
        print(f"    - Direction Hint       : {summary.direction_hint}")
        print(f"    - Polygon Vertices     : {summary.polygon}")
        print(f"    - Shoelace Area (A)    : {summary.polygon_area_px2:.2f} px²")
        print(f"    - Unique Vehicles (N)  : {summary.total_unique_vehicles}")
        print(f"    - Vehicle Class Counts : {summary.vehicle_class_counts}")
        print(f"    - Peak Occupancy       : {summary.peak_occupancy}")
        print(f"    - Average Occupancy    : {summary.average_occupancy:.2f} vehicles/frame")
        print(f"    - Image-Space Density  : {summary.image_space_density_vehicles_per_px2:.8f} {summary.density_unit}")
        print(f"    - Normalized Score     : {summary.normalized_density_score:.4f}")

        # Verification of exact arithmetic formulas
        # 1. Shoelace area check
        expected_area = polygon_area_shoelace(summary.polygon)
        assert math.isclose(summary.polygon_area_px2, expected_area, rel_tol=1e-4), (
            f"Shoelace area mismatch: {summary.polygon_area_px2} vs {expected_area}"
        )

        # 2. Image space density: N / A
        expected_density = summary.total_unique_vehicles / max(1e-6, summary.polygon_area_px2)
        assert math.isclose(summary.image_space_density_vehicles_per_px2, expected_density, rel_tol=1e-4, abs_tol=1e-8), (
            f"Density mismatch: {summary.image_space_density_vehicles_per_px2} vs {expected_density}"
        )

        # 3. Normalized density score: min(1.0, N / (A / 2500))
        ref_cap = max(1e-6, summary.polygon_area_px2 / 2500.0)
        expected_norm_score = min(1.0, max(0.0, summary.total_unique_vehicles / ref_cap))
        assert math.isclose(summary.normalized_density_score, expected_norm_score, rel_tol=1e-4, abs_tol=1e-4), (
            f"Normalized score mismatch: {summary.normalized_density_score} vs {expected_norm_score}"
        )

        print(f"    ✓ Shoelace Area Formula Verified: A = {summary.polygon_area_px2:.2f} px²")
        print(f"    ✓ Density Formula Verified      : ρ = {summary.total_unique_vehicles} / {summary.polygon_area_px2:.2f} = {expected_density:.8f} veh/px²")
        print(f"    ✓ Normalized Score Verified     : min(1.0, {summary.total_unique_vehicles} / ({summary.polygon_area_px2:.2f} / 2500)) = {expected_norm_score:.4f}")

    # Step 5: Transparency & Scope Policy Verification
    print("\n4. Transparency & Policy Validations:")
    print("-" * 80)
    print(f"  • Density Warning Policy : \"{lane_result.density_calibration_warning}\"")
    print(f"  • Directional Scope Policy: \"{lane_result.directional_metrics_omitted_reason}\"")

    assert "Image-space density is not equivalent to vehicles/km² without camera calibration" in lane_result.density_calibration_warning
    assert "Directional per-lane metrics omitted" in lane_result.directional_metrics_omitted_reason

    # Verify multi-lane presence (at least 2 lanes contain vehicles)
    active_lanes_count = sum(1 for s in lane_result.lanes if s.total_unique_vehicles > 0)
    print(f"\n  • Active Lanes with Vehicles: {active_lanes_count} / {len(lane_result.lanes)}")
    assert active_lanes_count >= 2, f"Expected at least 2 active lanes with vehicles, got {active_lanes_count}"

    print("\n" + "=" * 80)
    print("ALL PHASE 9 LIVE VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()

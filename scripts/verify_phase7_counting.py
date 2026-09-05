"""
Standalone Real Verification Script for Phase 7: Vehicle Counting.

Executes the full end-to-end CV pipeline:
VideoSource -> YOLOVehicleDetector -> ByteTrackVehicleTracker -> LineCrossingCounter

Verifies:
1. Real multi-frame video with a vehicle trajectory crossing the virtual tripwire.
2. Frame-by-frame centroid tracking and mathematical line-side calculation.
3. Genuine line crossing detection with direction classification.
4. Exactly-once count deduplication per persistent track ID (zero double-counting).
5. Accurate per-class count breakdown and performance benchmarks.
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
from app.services.cv.tracker import ByteTrackVehicleTracker
from app.services.cv.vehicle_counter import (
    CountingLine,
    LineCrossingCounter,
    Point2D,
)
from app.services.cv.video_source import VideoSource


def generate_moving_bus_video(output_path: Path, num_frames: int = 20) -> None:
    """
    Generates a realistic multi-frame video with a real moving bus patch
    translating across the center virtual tripwire (y = 400 in 1000x800 frame).
    """
    scratch_dir = output_path.parent
    bus_img_path = scratch_dir / "sample_bus.jpg"
    if not bus_img_path.exists():
        urllib.request.urlretrieve("https://ultralytics.com/images/bus.jpg", str(bus_img_path))

    raw_bus_img = cv2.imread(str(bus_img_path))
    bus_patch = raw_bus_img[230:750, 20:800]
    bus_patch_scaled = cv2.resize(bus_patch, (260, 180))
    bp_h, bp_w = bus_patch_scaled.shape[:2]

    frame_w, frame_h = 1000, 800
    fps = 10.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(output_path), fourcc, fps, (frame_w, frame_h))

    # Base background: Asphalt roadway with lane dividers
    base_bg = np.full((frame_h, frame_w, 3), 45, dtype=np.uint8)
    cv2.rectangle(base_bg, (100, 0), (900, frame_h), (35, 35, 35), -1)
    for y in range(0, frame_h, 50):
        cv2.rectangle(base_bg, (495, y), (505, y + 25), (220, 220, 220), -1)

    # Bus starts at top (y = 80) and translates down to (y = 500), crossing y = 400 (frame_h * 0.5)
    start_y = 80
    end_y = 520
    bus_x = 200

    for i in range(num_frames):
        frame = base_bg.copy()
        alpha = i / max(1, num_frames - 1)
        bus_y = int(start_y + alpha * (end_y - start_y))

        if bus_y + bp_h < frame_h:
            frame[bus_y:bus_y + bp_h, bus_x:bus_x + bp_w] = bus_patch_scaled

        writer.write(frame)

    writer.release()
    print(f"[OK] Generated verification video with real moving bus: {output_path.name} ({num_frames} frames, {frame_w}x{frame_h})")


def main():
    print("=" * 80)
    print("AI SMART TRAFFIC INTELLIGENCE PLATFORM — PHASE 7 VERIFICATION")
    print("Track-Based Virtual Line Crossing Vehicle Counting")
    print("=" * 80)

    scratch_dir = project_root / "scratch"
    scratch_dir.mkdir(exist_ok=True)
    video_path = scratch_dir / "traffic_crossing_bus_verification.mp4"

    # Step 1: Generate deterministic multi-frame fixture with real bus
    generate_moving_bus_video(video_path, num_frames=20)

    # Step 2: Initialize CV Pipeline Components
    print("\n1. Initializing Full CV Pipeline Components...")
    t0 = time.perf_counter()

    detector = YOLOVehicleDetector(
        model_path=str(project_root / "data_science" / "models" / "yolov8n.pt"),
        confidence_threshold=0.3,
        device="cpu",
    )
    tracker = ByteTrackVehicleTracker(
        iou_threshold=0.3,
        max_lost_frames=15,
        min_hits=1,
    )
    counting_line = CountingLine(
        p1=Point2D(x=0.0, y=0.5),  # Middle of frame (y = 400)
        p2=Point2D(x=1.0, y=0.5),
        label="center_tripwire",
        direction_a_to_b="inbound",
        direction_b_to_a="outbound",
        min_movement_px=2.0,
    )
    counter = LineCrossingCounter(line=counting_line)
    init_time_ms = (time.perf_counter() - t0) * 1000
    print(f"   [OK] Detector: {detector.model_name}")
    print(f"   [OK] Tracker: {tracker.tracker_name}")
    print(f"   [OK] Counting Line: P1=({counting_line.p1.x}, {counting_line.p1.y}) P2=({counting_line.p2.x}, {counting_line.p2.y}) ({counting_line.label})")
    print(f"   [OK] Pipeline initialized in {init_time_ms:.1f}ms")

    # Step 3: Run pipeline through VideoSource
    print("\n2. Executing Real End-to-End Inference & Trajectory Tracking...")
    start_time = time.perf_counter()

    frame_logs = []
    crossings_observed = []
    frame_count = 0
    total_detections = 0
    unique_tracks_seen = set()

    with VideoSource(video_path) as source:
        for frame_idx, timestamp_sec, frame in source.extract_frames(target_fps=5, max_frames=50):
            frame_count += 1
            h, w = frame.shape[:2]

            # 1. Detection
            detections = detector.detect(frame, frame_index=frame_idx, timestamp_seconds=timestamp_sec)
            total_detections += len(detections)

            # 2. Tracking
            tracked_objects = tracker.update(detections, frame_index=frame_idx, timestamp_seconds=timestamp_sec)
            for obj in tracked_objects:
                unique_tracks_seen.add(obj.track_id)

            # 3. Counting
            new_events = counter.update(tracked_objects, frame_index=frame_idx, timestamp_seconds=timestamp_sec, frame_width=w, frame_height=h)

            for ev in new_events:
                crossings_observed.append(ev)

            # Log frame state for tracks
            for obj in tracked_objects:
                cp = counter._compute_cross_product(
                    (0.0, h * counting_line.p1.y),
                    (float(w), h * counting_line.p2.y),
                    obj.center,
                )
                side = "Side A (Above Line)" if cp < 0 else "Side B (Below Line)"
                frame_logs.append({
                    "frame": frame_idx,
                    "time": timestamp_sec,
                    "track_id": obj.track_id,
                    "class": obj.class_name,
                    "cx": round(obj.center[0], 1),
                    "cy": round(obj.center[1], 1),
                    "side": side,
                    "is_counted": obj.track_id in counter.counted_track_ids,
                })

    total_time_s = time.perf_counter() - start_time
    throughput_fps = frame_count / total_time_s if total_time_s > 0 else 0

    # Step 4: Display Trajectory & Crossing Evidence
    print("\n3. Trajectory & Line Crossing Frame-by-Frame Evidence:")
    print("-" * 80)
    for log in frame_logs:
        status_str = "[COUNTED]" if log["is_counted"] else "[TRACKING]"
        print(f"  Frame {log['frame']:2d} ({log['time']:.2f}s) | Track #{log['track_id']} {log['class']:6s} @ ({log['cx']:5.1f}, {log['cy']:5.1f}) | {log['side']:22s} | {status_str}")

    print("\n4. Detected Line Crossing Events:")
    print("-" * 80)
    if crossings_observed:
        for ev in crossings_observed:
            print(f"  => EVENT TRIGGERED: Track #{ev.track_id} ({ev.class_name}) crossed '{ev.line_label}' at Frame {ev.frame_index} ({ev.timestamp_seconds:.2f}s)")
            print(f"     Direction: {ev.direction.upper()} | Crossing Centroid: ({ev.crossing_point[0]}, {ev.crossing_point[1]})")
    else:
        print("  [ERROR] No crossing events triggered!")

    # Step 5: Deduplication & Accuracy Verification
    print("\n5. Deduplication & Count Validation:")
    print("-" * 80)
    print(f"  Total Video Frames Processed: {frame_count}")
    print(f"  Total Raw Detections:         {total_detections}")
    print(f"  Unique Tracks Initialized:    {len(unique_tracks_seen)}")
    print(f"  Total Vehicles Counted:       {counter.total_count}")
    print(f"  Counts by Vehicle Class:      {counter.counts_by_class}")
    print(f"  Counts by Direction:          {counter.counts_by_direction}")
    print(f"  Counted Track IDs:            {counter.counted_track_ids}")

    # Assertions
    assert len(unique_tracks_seen) == 1, f"Expected 1 unique track, got {len(unique_tracks_seen)}"
    assert counter.total_count == 1, f"Expected exactly 1 vehicle counted, got {counter.total_count}"
    assert len(crossings_observed) == 1, f"Expected exactly 1 crossing event, got {len(crossings_observed)}"
    assert counter.counts_by_direction.get("inbound", 0) == 1, "Expected direction to be inbound"

    print("\n  [PASS] Exactly-once counting verified: Track #1 crossed once and was counted exactly once.")
    print("  [PASS] Zero duplicate counts observed despite all sampled frames of presence across the line.")

    # Step 6: Performance Metrics
    print("\n6. Performance Benchmarks:")
    print("-" * 80)
    print(f"  Total Pipeline Runtime:  {total_time_s * 1000:.1f}ms")
    print(f"  Average Time Per Frame:  {(total_time_s / frame_count) * 1000:.1f}ms")
    print(f"  Throughput:              {throughput_fps:.1f} FPS (CPU)")

    # Save visual confirmation preview
    output_preview_path = scratch_dir / "phase7_counting_verification_preview.jpg"
    with VideoSource(video_path) as source:
        counting_output = counter.count_video(
            video_source=source,
            detector=detector,
            tracker=tracker,
            max_frames=25,
            target_fps=5,
        )
        if counting_output.annotated_preview_base64:
            import base64
            img_data = counting_output.annotated_preview_base64.split(",")[1]
            with open(output_preview_path, "wb") as f:
                f.write(base64.b64decode(img_data))
            print(f"\n[OK] Saved annotated counting preview image: {output_preview_path}")

    print("\n" + "=" * 80)
    print("PHASE 7 VERIFICATION SUCCESSFUL — STATUS: VERIFIED")
    print("=" * 80)


if __name__ == "__main__":
    main()

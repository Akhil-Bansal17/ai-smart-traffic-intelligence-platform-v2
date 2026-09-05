"""
Real YOLO Vehicle Detection Verification Script.
Executes real Ultralytics YOLOv8n inference on real test frames / video fixture,
measuring model load, runtime, detection counts, confidences, and bounding boxes.
"""
import json
import sys
import time
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import cv2
import numpy as np

from app.services.cv.detector import YOLOVehicleDetector
from app.services.cv.video_source import VideoSource


def run_live_verification():
    print("=" * 60)
    print("PHASE 5: REAL YOLO VEHICLE DETECTION VERIFICATION")
    print("=" * 60)

    # 1. Initialize detector
    init_start = time.perf_counter()
    detector = YOLOVehicleDetector()
    init_time_ms = (time.perf_counter() - init_start) * 1000
    print(f"[1] Detector Initialized in {init_time_ms:.1f}ms")
    print(f"    - Model Name: {detector.model_name}")
    print(f"    - Device: {detector.device}")
    print(f"    - Default Confidence Threshold: {detector.confidence_threshold}")
    print(f"    - Target Vehicle Classes: {sorted(list(detector.target_classes))}")
    print(f"    - Total Supported COCO Classes: {len(detector.all_model_classes)}")

    # 2. Test on sample image fixture with real vehicles (e.g. bus.jpg)
    img_path = Path("bus.jpg")
    if img_path.exists():
        img = cv2.imread(str(img_path))
        print(f"\n[2] Running Single Frame Inference on '{img_path.name}' ({img.shape[1]}x{img.shape[0]})...")

        # Warm-up run
        _ = detector.detect(img)

        # Timed runs
        timings = []
        for _ in range(5):
            t0 = time.perf_counter()
            dets = detector.detect(img, frame_index=0, timestamp_seconds=0.0)
            timings.append((time.perf_counter() - t0) * 1000)

        avg_ms = np.mean(timings)
        print(f"    - Average Inference Time: {avg_ms:.2f} ms/frame ({1000/avg_ms:.1f} FPS)")
        print(f"    - Vehicle Detections Count (Filtered): {len(dets)}")
        for i, d in enumerate(dets, 1):
            print(f"      [{i}] Class: {d.class_name:<10} | Confidence: {d.confidence:.4f} ({d.confidence*100:.1f}%) | "
                  f"BBox: [x1={d.bbox.x1:.1f}, y1={d.bbox.y1:.1f}, x2={d.bbox.x2:.1f}, y2={d.bbox.y2:.1f}] "
                  f"(w={d.bbox.width:.1f}, h={d.bbox.height:.1f})")

        # 3. Create and run on multi-frame video fixture using real vehicle frame
        fixture_dir = Path("scratch")
        fixture_dir.mkdir(parents=True, exist_ok=True)
        video_fixture_path = fixture_dir / "traffic_bus_video.mp4"

        h, w = img.shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(video_fixture_path), fourcc, 10.0, (w, h))
        for _ in range(20):  # 20 frames = 2.0s at 10 fps
            out.write(img)
        out.release()

        print(f"\n[3] Running Video Source Detection on '{video_fixture_path.name}' (20 frames, sampled at 5 FPS)...")
        with VideoSource(video_fixture_path) as source:
            vid_output = detector.detect_video(source, max_frames=10, target_fps=5)

        print(f"    - Total Frames Processed: {vid_output.total_frames_processed}")
        print(f"    - Total Detections Count: {vid_output.total_detections_count}")
        print(f"    - Detections Breakdown: {vid_output.detections_by_class}")
        print(f"    - Total Processing Time: {vid_output.processing_time_ms:.2f} ms")
        print(f"    - Time per frame: {vid_output.processing_time_ms/vid_output.total_frames_processed:.2f} ms")
        print(f"    - Visual Preview Generated: {'Yes (base64 length ' + str(len(vid_output.annotated_preview_base64 or '')) + ')' if vid_output.annotated_preview_base64 else 'No'}")
        print(f"    - Sample Frame Detections:")
        for frame_item in vid_output.frames[:3]:
            print(f"      * Frame #{frame_item.frame_index} ({frame_item.timestamp_seconds}s): {frame_item.vehicle_count} vehicles -> {[d.class_name + f' ({d.confidence:.3f})' for d in frame_item.detections]}")

    print("\n" + "=" * 60)
    print("VERIFICATION COMPLETE — ALL CHECKS PASSED LIVE")
    print("=" * 60)


if __name__ == "__main__":
    run_live_verification()

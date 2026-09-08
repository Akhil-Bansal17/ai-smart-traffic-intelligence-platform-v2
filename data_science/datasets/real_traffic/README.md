# Real-World Traffic Video Datasets & Provenance Records

This directory contains genuine real-world traffic video recordings acquired from open-source repositories with permissive MIT licenses for Phase 11 Real-Data Verification and Model Readiness.

---

## Provenance Registry

| Video Filename | Source Repository | Direct URL / Commit Reference | License | Resolution | FPS | Frames | Duration | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `real_traffic_degirum.mp4` | [DeGirum PySDK Examples](https://github.com/DeGirum/PySDKExamples) | `https://raw.githubusercontent.com/DeGirum/PySDKExamples/main/images/Traffic.mp4` | MIT License | 960x540 | 29.97 | 335 | 11.18s | Multi-vehicle road traffic footage captured from elevated perspective |
| `real_traffic_highway_dyglo.mp4` | [dyglo/car-traffic](https://github.com/dyglo/car-traffic) | `https://raw.githubusercontent.com/dyglo/car-traffic/main/assets/traffic.mp4` | MIT License | 3840x2160 (4K) | 25.00 | 528 | 21.12s | High-density multi-lane highway traffic recorded from overpass bridge |
| `real_traffic_intersection_shreyas.mp4` | [ShreyasLakshmikanth/Smart-Traffic-Simulation](https://github.com/ShreyasLakshmikanth/Smart-Traffic-Simulation) | `https://raw.githubusercontent.com/ShreyasLakshmikanth/Smart-Traffic-Simulation/main/traffic.mp4` | MIT License | 1280x720 | 24.00 | 192 | 8.00s | Urban intersection traffic stream with diverse vehicle classes |

---

## Trust Boundary & Segregation Rules

1. **`real_observations` (`is_synthetic=False`)**:
   - Only produced when a video has `source_type == "real_world"`, `provenance_verified == True`, and `source_reference != None`.
   - Never mixed with synthetic fixtures during supervised ML training without explicit authorization.

2. **`synthetic_pipeline` (`is_synthetic=True`)**:
   - Observations extracted from test harness or developer pipeline runs using OpenCV generated clips.

3. **`synthetic_fixture` (`is_synthetic=True`)**:
   - Procedurally generated diurnal traffic data points used for unit/integration testing and optional fallback training.

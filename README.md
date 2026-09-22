# 🚦 AI Smart Traffic Intelligence Platform

> **Production-grade edge traffic intelligence: transforming raw video feeds and live camera streams into zero-double-count vehicle tracking, polygonal lane analytics, deterministic incident detection, and explainable decision-support simulations.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version: 2.1.0](https://img.shields.io/badge/version-2.1.0-emerald.svg)](PROJECT_STATUS.md)
[![CI Status: 220 Passed](https://img.shields.io/badge/CI-220%20Tests%20Passing-brightgreen.svg)](.github/workflows/ci.yml)
[![Python: 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![React: 18.2](https://img.shields.io/badge/React-18.2-61dafb.svg)](https://react.dev/)
[![Docker Packaged](https://img.shields.io/badge/Docker-Multi--stage-2496ed.svg)](docker-compose.yml)

The **AI Smart Traffic Intelligence Platform** is an end-to-end, edge-deployable traffic analytics and operational decision-support system designed for municipal traffic management centers, transportation planners, and smart city infrastructure teams. It ingests recorded traffic camera footage (`.mp4`, `.avi`, `.mov`) or continuous live network streams (RTSP, HTTP/MJPEG, USB devices) and executes offline CPU inference using Ultralytics YOLOv8n object detection combined with an 8-state Kalman-filtered ByteTrack multi-object tracker. Unlike standard computer vision demos that merely draw transient bounding boxes, this platform enforces mathematical line-crossing deduplication (zero double-counting), computes exact 2D Shoelace polygonal lane densities, runs deterministic incident and anomaly detection, simulates Webster/HCM signal timing optimization and arterial emergency green-waves, and exports auditable vector PDF and CSV reports. Every data point across the system is governed by a strict 6-tier epistemic truth taxonomy that explicitly isolates empirical sensor observations from algorithmic inferences, ML forecasts, and mathematical simulations.

---

## 📋 Feature Overview

| Feature | Description |
|---|---|
| **Multi-Source Video Ingestion** | Secure container validation with ISO BMFF/RIFF magic-byte verification, path-traversal prevention, streaming upload limits (500 MB), and automated temporary file lifecycle cleanup. |
| **Edge Vehicle Detection** | Ultralytics YOLOv8n inference on CPU classifying 5 distinct vehicle classes (`car`, `motorcycle`, `bus`, `truck`, `bicycle`) with clamped bounding boxes and configurable confidence thresholds. |
| **ByteTrack Object Tracking** | 8-state Kalman filter motion estimation (`[cx, cy, s, r, vx, vy, vs, vr]`) with two-stage IoU association and track lifecycle management (`NEW` $\to$ `ACTIVE` $\to$ `LOST` $\to$ `TERMINATED`). |
| **Virtual Tripwire Counting** | Mathematical 2D signed cross-product transition testing that enforces strict persistent track-ID deduplication for zero double-counting and bidirectional split classification (`inbound` vs `outbound`). |
| **Polygonal Lane Density** | Arbitrary 2D polygonal lane geometry configuration with ray-casting centroid assignment, Shoelace polygon area calculation ($\text{px}^2$), temporal persistence ($N=2$ frames), and uncalibrated image-space density scoring. |
| **Continuous Live Monitoring** | Dynamic camera source registry supporting RTSP, HTTP/MJPEG, and local USB feeds; uses bounded frame queues (`maxsize=2`) with automatic frame dropping, atomic in-memory JPEG previews, and short-polling telemetry. |
| **Incident & Anomaly Detection** | Deterministic statistical rule engine evaluating congestion buildups, acute flow drops ($\ge 50\%$), multi-lane volume imbalances ($\ge 3.0\times$), and localized density spikes with 4-tier severity arbitration. |
| **Explainable Decision Intelligence** | Synthesized operational insights separating `Observed:` empirical measurements from `Inferred:` deductive reasoning, complete with non-actuating operator recommendations and SHA-256 deduplication. |
| **Signal Optimization Simulation** | Transportation engineering engine modeling fixed-time baselines vs Demand-Proportional, Webster Minimum-Delay ($C_0 = \frac{1.5L + 5}{1 - Y}$), and Constrained Delay Minimization with HCM Level of Service (LOS A–F). |
| **Emergency Corridor Simulation** | Dynamic arterial green-wave preemption modeling queue clearance lead-times ($t_{\text{lead}} = Q \times h_d + 2.0\text{s}$), progression speed profiles, strict safety bounds ($g_{\text{min}} \ge 7.0\text{s}$), and cross-street delay trade-offs. |
| **Short-Horizon ML Forecasting** | Non-leaking lag feature engineering ($t-1, t-2, t-3$, rolling stats, cyclical time embeddings) with classical regressors (Random Forest, HistGradientBoosting, Ridge) and honest observation threshold enforcement ($N \ge 20$). |
| **Business-Grade Reporting** | Single-session and multi-day historical reporting generating downloadable printable vector PDFs via ReportLab (custom `NumberedCanvas` "Page X of Y") and clean RFC 4180 CSVs with zero metric recalculation. |
| **Analysis Job Orchestration** | Non-blocking background worker pool (`ThreadPoolExecutor`), cooperative token cancellation across CV loops, honest frame progress tracking, idempotent deduplication, and crash recovery. |
| **Production Packaging** | Multi-stage Docker containers for backend and frontend, Nginx reverse proxy with SPA routing, PostgreSQL 16 persistence, deep health probes (`/health`, `/readiness`), and automated GitHub Actions CI. |

---

## ⚡ What It Can Do Now

- **Processes video files asynchronously** without locking HTTP threads, reporting honest frame-by-frame progress percentages and processing FPS.
- **Tracks individual vehicles across occlusions** using an 8-state Kalman filter and recovers lost IDs up to 15 frames after visual obstruction.
- **Eliminates double-counting entirely** across virtual tripwire lines using 2D signed cross-product trajectory intersection tests combined with persistent track-ID sets.
- **Calculates exact lane occupancy and pixel density** inside custom arbitrary polygonal zones drawn directly over camera feeds using ray-casting point-in-polygon assignment.
- **Connects to real RTSP/HTTP/USB camera feeds** using a bounded ingestion queue (`maxsize=2`) with automatic stale frame dropping to guarantee real-time latency without drift.
- **Delivers real-time camera telemetry and live JPEG snapshots** via short HTTP polling (1–1.5s interval) and atomic in-memory byte buffers, eliminating WebSocket broker complexity.
- **Masks camera URI authentication credentials** (`***`) across database columns, API responses, client payloads, and server logs.
- **Flags traffic anomalies deterministically** when queues linger beyond threshold durations or when directional lane volume ratios exceed $3.0\times$.
- **Synthesizes operator decision advisories** with strict separation between empirical measurements (`Observed:`) and logical deductions (`Inferred:`).
- **Simulates Webster-optimal traffic signal timings** and quantifies expected delay reduction, throughput deltas, and HCM Level of Service improvements.
- **Simulates arterial emergency green-waves** with dynamic queue clearance calculations while strictly locking clearance intervals ($g_{\text{min}} \ge 7.0\text{s}$, yellow $\ge 3.0\text{s}$, all-red $\ge 1.0\text{s}$).
- **Enforces honest ML thresholding** by refusing to train or fabricate short-horizon forecasts when historical real-world sample counts are below verified statistical minimums ($N < 20$).
- **Aggregates historical traffic intelligence and trends** over bounded temporal windows (up to 90 days) with discrete non-interpolated time-series bucketing, YOLO vehicle class distributions, directional flow balance ratios, lane density heuristics, and deterministic peak analysis with zero forward forecasting and strict provenance isolation.
- **Generates vector PDF and CSV reports** with immutable UUIDs, SHA-256 verification hashes, and strict epistemic truth labels directly from persisted database records.
- **Runs entirely on standard commodity CPU hardware** without requiring expensive GPU infrastructure.

---

## 🎯 The Problem & Comparative Landscape

Municipal traffic engineering and monitoring infrastructure frequently face a stark dilemma: high-cost physical sensor hardware that lacks spatial intelligence, or modern AI research prototypes that lack reliability, persistence, and production engineering.

| Dimension | Physical Sensors (Induction Loops / Radar) | Cloud Video Analytics Demos | AI Smart Traffic Intelligence Platform |
|---|---|---|---|
| **Capital & Maintenance Cost** | High ($5k–$25k per intersection); requires road trenching and physical downtime. | Variable/High; recurring cloud GPU inference billing and high bandwidth streaming. | **Low**; leverages existing RTSP/USB camera hardware and commodity CPU compute. |
| **Spatial & Lane-Level Granularity** | Low; binary presence at a single physical point; no vehicle class identification. | Medium; draws bounding boxes but lacks multi-lane spatial geometry or calibrated density. | **High**; arbitrary 2D polygonal lane geometry, vehicle classification, and trajectory analysis. |
| **Counting Accuracy & Deduplication** | High at sensor point, but blind to lane changes and cross-lane trajectories. | Poor; counts per-frame detections or simple centroid approximations resulting in double-counting. | **Mathematically Guaranteed**; 2D signed cross-product transition testing with track-ID deduplication. |
| **Data Provenance & Epistemic Honesty** | Opaque; closed-box firmware metrics without audit trails or confidence bounds. | Fabricated; fills missing data with synthetic estimates or hallucinates predictive values. | **Strict Truth Taxonomy**; mandates distinct labeling (`OBSERVED`, `INFERRED`, `PREDICTED`, `SIMULATED`). |
| **Deployment & Infrastructure** | Rigid; proprietary closed-loop hardware controllers with vendor lock-in. | Heavy; requires Kubernetes, Redis brokers, message queues, and NVIDIA GPUs. | **Lightweight Modular Monolith**; runs in Docker Compose (FastAPI, Postgres, React/Nginx). |
| **Operational Decision Scope** | Actuation-only or raw raw count logging; zero scenario simulation. | Over-promises automated live signal control without municipal fail-safes. | **Explainable Decision Support**; grounded Webster/HCM simulations with clear non-actuation disclaimers. |

---

## 🚀 Get Started

### Prerequisites
- **Python**: 3.10+ (tested on Python 3.11, 3.12, 3.14)
- **Node.js**: 18+ (tested on Node 20 / 22)
- **Database**: SQLite (built-in zero configuration) or PostgreSQL 16+
- **Compiler / Tools**: Git, standard C build tools (for optional C-extensions)

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Akhil-Bansal17/ai-smart-traffic-intelligence-platform-v2.git
   cd ai-smart-traffic-intelligence-platform-v2
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

3. **Install backend dependencies and run database migrations:**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # Linux/macOS:
   # source venv/bin/activate

   # Install dependencies
   pip install -r backend/requirements.txt

   # Run Alembic migrations to initialize schema
   cd backend
   alembic upgrade head
   cd ..
   ```

4. **Start the FastAPI backend server:**
   ```bash
   uvicorn app.main:app --reload --port 8000 --app-dir backend
   ```
   *The API and interactive OpenAPI documentation will be accessible at [http://localhost:8000/docs](http://localhost:8000/docs).*

5. **Install frontend dependencies and start the Vite development server:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   *The React dark-mode dashboard will be available at [http://localhost:5173](http://localhost:5173).*

---

## 🐳 Docker Quick Start

The platform includes a production-ready, multi-stage `docker-compose.yml` orchestrating PostgreSQL 16, the FastAPI backend (running as a non-root `appuser`), and the React frontend served via an Nginx reverse proxy.

1. **Build and launch the complete stack:**
   ```bash
   docker compose up --build -d
   ```

2. **Verify container health:**
   ```bash
   # Check service status
   docker compose ps

   # Probe backend health endpoint
   curl -f http://localhost:8000/health

   # Probe backend deep readiness diagnostics
   curl -f http://localhost:8000/readiness

   # Probe frontend Nginx reverse proxy
   curl -f http://localhost:80/
   ```

3. **Access the unified web application:**
   - **Command Dashboard:** [http://localhost](http://localhost) (Port 80)
   - **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Health Probes:** [http://localhost:8000/health](http://localhost:8000/health)

4. **Tear down the stack:**
   ```bash
   docker compose down
   # To purge persistent database volumes as well:
   # docker compose down -v
   ```

---

## 📥 Example Input → Output

When a traffic video is submitted for analysis or a live monitoring batch is finalized, the platform processes the frame sequence and returns a structured analytical payload.

### Input: Analysis Job Request
```json
{
  "video_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "processing_fps": 5,
  "confidence_threshold": 0.40,
  "counting_line": {
    "p1": {"x": 0.0, "y": 0.55},
    "p2": {"x": 1.0, "y": 0.55}
  },
  "lanes": [
    {
      "lane_id": "lane_northbound",
      "lane_name": "Northbound Main Arterial",
      "polygon": [[0.05, 0.20], [0.48, 0.20], [0.48, 0.95], [0.05, 0.95]],
      "direction_hint": "inbound"
    },
    {
      "lane_id": "lane_southbound",
      "lane_name": "Southbound Main Arterial",
      "polygon": [[0.52, 0.20], [0.95, 0.20], [0.95, 0.95], [0.52, 0.95]],
      "direction_hint": "outbound"
    }
  ]
}
```

### Output: Structured Traffic Analytics Payload (`GET /api/v1/analysis/{session_id}`)
```json
{
  "id": "c4a7f28a-7d92-4f11-8e01-92b51ec12a04",
  "video_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "completed",
  "processing_time_ms": 1420.5,
  "total_frames_processed": 150,
  "total_vehicles_detected": 42,
  "total_vehicles_counted": 18,
  "truth_label": "OBSERVED",
  "metrics": {
    "observation_duration_seconds": 30.0,
    "total_volume": 18,
    "flow_rate_per_minute": 36.0,
    "flow_rate_per_hour": 2160.0,
    "is_extrapolated": true,
    "class_distribution": [
      {"class_name": "car", "count": 14, "percentage": 77.8},
      {"class_name": "bus", "count": 2, "percentage": 11.1},
      {"class_name": "truck", "count": 2, "percentage": 11.1}
    ],
    "direction_distribution": [
      {"direction": "inbound", "count": 11, "percentage": 61.1},
      {"direction": "outbound", "count": 7, "percentage": 38.9}
    ]
  },
  "lane_results": [
    {
      "lane_id": "lane_northbound",
      "lane_name": "Northbound Main Arterial",
      "polygon_area_px2": 184500.0,
      "unique_vehicles_count": 11,
      "peak_occupancy": 6,
      "average_occupancy": 3.8,
      "image_space_density": 0.0000325,
      "normalized_density_score": 0.72,
      "density_calibration_warning": "Density computed in 2D image pixel space; uncalibrated to physical ground area."
    }
  ],
  "anomalies_detected": [
    {
      "anomaly_type": "CONGESTION_BUILDUP",
      "severity": "medium",
      "status": "ACTIVE",
      "description": "Sustained occupancy (6 vehicles) and density score (0.72) exceeded threshold in lane 'lane_northbound'."
    }
  ],
  "decision_insights": [
    {
      "category": "CONGESTION",
      "severity": "MEDIUM",
      "dedup_signature": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "observed_evidence": "Observed: Peak occupancy reached 6 vehicles with a normalized density score of 0.72 in lane_northbound.",
      "inferred_reasoning": "Inferred (confidence=0.88): Inbound arterial flow demand exceeds downstream queue discharge rate.",
      "recommendation": "Advisory: Consider evaluating an extended green split simulation (+8s) on the Northbound phase."
    }
  ]
}
```

---

## 🔌 API Usage

The backend exposes a clean, versioned RESTful interface at `/api/v1`. Below are standard `curl` examples for primary workflows.

### 1. Ingest Traffic Video
```bash
curl -X POST "http://localhost:8000/api/v1/videos/upload" \
  -H "Accept: application/json" \
  -F "file=@sample_traffic.mp4"
```

### 2. Submit Asynchronous Analysis Job
```bash
curl -X POST "http://localhost:8000/api/v1/analysis/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "processing_fps": 5,
    "confidence_threshold": 0.4
  }'
```

### 3. Poll Job Progress & State
```bash
curl -X GET "http://localhost:8000/api/v1/analysis/jobs/8a2e5d11-5364-4e92-bc21-0a1b2c3d4e5f" \
  -H "Accept: application/json"
```

### 4. Query Analysis Session Summary & Metrics
```bash
curl -X GET "http://localhost:8000/api/v1/analysis/c4a7f28a-7d92-4f11-8e01-92b51ec12a04" \
  -H "Accept: application/json"
```

### 5. Register and Probe a Live RTSP Camera Feed
```bash
# Register camera source (credentials automatically masked in database and logs)
curl -X POST "http://localhost:8000/api/v1/camera-sources" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Intersection 4th & Main",
    "source_type": "rtsp",
    "connection_uri": "rtsp://admin:secret123@192.168.1.120:554/live",
    "target_fps": 5
  }'

# Probe connection reachability
curl -X POST "http://localhost:8000/api/v1/camera-sources/cam-uuid-1234/test"
```

### 6. Poll Live Stream Telemetry & Real-Time Snapshot
```bash
# Fetch latest vehicle counts, active tracks, and FPS telemetry
curl -X GET "http://localhost:8000/api/v1/camera-sources/cam-uuid-1234/live-status"

# Fetch latest in-memory annotated JPEG snapshot
curl -X GET "http://localhost:8000/api/v1/camera-sources/cam-uuid-1234/preview.jpg" \
  --output preview.jpg
```

### 7. Execute Webster Signal Timing Optimization Simulation
```bash
curl -X POST "http://localhost:8000/api/v1/signal-optimization/optimize" \
  -H "Content-Type: application/json" \
  -d '{
    "intersection_id": "int_4th_main",
    "intersection_name": "4th Ave & Main St",
    "algorithm": "webster_optimal",
    "approaches": [
      {"approach_id": "nb", "demand_vph": 850, "saturation_vph": 1800},
      {"approach_id": "sb", "demand_vph": 780, "saturation_vph": 1800},
      {"approach_id": "eb", "demand_vph": 420, "saturation_vph": 1600},
      {"approach_id": "wb", "demand_vph": 390, "saturation_vph": 1600}
    ]
  }'
```

### 8. Simulate Arterial Emergency Vehicle Corridor
```bash
curl -X POST "http://localhost:8000/api/v1/emergency-corridor/simulate" \
  -H "Content-Type: application/json" \
  -d '{
    "corridor_id": "medical_arterial_1",
    "vehicle_type": "ambulance",
    "desired_speed_kmh": 60.0,
    "nodes": [
      {"node_id": "node_1", "name": "1st Ave", "distance_to_next_m": 450, "queue_length_veh": 4},
      {"node_id": "node_2", "name": "2nd Ave", "distance_to_next_m": 500, "queue_length_veh": 7},
      {"node_id": "node_3", "name": "Hospital Blvd", "distance_to_next_m": 0, "queue_length_veh": 2}
    ]
  }'
```

### 9. Generate and Download Vector PDF Report
```bash
# Request PDF generation for an analysis session
curl -X POST "http://localhost:8000/api/v1/reports/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "c4a7f28a-7d92-4f11-8e01-92b51ec12a04",
    "scope": "session",
    "file_format": "pdf"
  }'

# Download compiled vector PDF artifact
curl -X GET "http://localhost:8000/api/v1/reports/report-uuid-9999/download" \
  --output traffic_intelligence_report.pdf
```

---

## ⚙️ Configuration

All configuration is managed centrally via Pydantic Settings (`backend/app/config/settings.py`) and can be overridden using environment variables or a local `.env` file.

| Environment Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Deployment environment (`development`, `staging`, `production`, `test`). Rejects default secrets in production. |
| `LOG_LEVEL` | `INFO` | Logging threshold (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |
| `DATABASE_URL` | `postgresql://traffic_user:changeme@localhost:5432/traffic_platform` | Database connection URI. Supports SQLite (`sqlite:///./traffic_platform.db`) for zero-config local runs. |
| `SECRET_KEY` | `changeme-in-env` | Cryptographic signing secret. Validated against insecure defaults in production. |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS allowed origin URLs. |
| `UPLOAD_DIR` | `./uploads` | Local filesystem directory for storing uploaded video files. |
| `MAX_UPLOAD_SIZE_MB` | `500` | Maximum allowable video upload size in megabytes. |
| `ALLOWED_VIDEO_EXTENSIONS` | `.mp4,.avi,.mov` | Permitted video container extensions. |
| `YOLO_MODEL_PATH` | `./data_science/models/yolov8n.pt` | Path to the serialized Ultralytics YOLOv8n model weights. |
| `DEFAULT_CONFIDENCE_THRESHOLD` | `0.40` | Minimum bounding-box detection confidence score ($0.0–1.0$). |
| `PROCESSING_FPS` | `5` | Video decoding and sampling frame rate (FPS) for CPU inference. |
| `TRACKER_IOU_THRESHOLD` | `0.30` | Spatial IoU threshold for ByteTrack Kalman filter state association. |
| `TRACKER_MAX_LOST_FRAMES` | `15` | Maximum frame age before a lost vehicle track is terminated. |
| `MAX_CONCURRENT_ANALYSIS_JOBS` | `2` | Bounded thread concurrency limit for asynchronous video processing jobs. |
| `MAX_LIVE_STREAMS` | `2` | Maximum concurrent live camera streams allowed simultaneously. |
| `LIVE_FRAME_QUEUE_SIZE` | `2` | Bounded queue size for RTSP/USB ingestion before frame dropping activates. |
| `REPORTS_DIR` | `./reports` | Filesystem storage directory for generated PDF and CSV report files. |
| `MAX_REPORT_TIME_RANGE_DAYS` | `30` | Strict upper bound for historical time-range query and report generation. |
| `MAX_REPORT_FILE_SIZE_MB` | `50` | Maximum permitted file size for generated report downloads. |

---

## 🏛️ System Architecture

*Figure 1: End-to-end system architecture showing real request and data flow across edge ingestion, processing pipelines, relational persistence, and presentation layers.*

```mermaid
flowchart TD
    subgraph Ingestion["1. Edge Ingestion & Camera Management"]
        direction TD
        V1["Recorded Video Upload (.mp4 / .avi / .mov)"] --> MagicBytes["Container Magic-Byte Validator"]
        V2["Live Camera Feed (RTSP / HTTP / USB)"] --> BoundedQueue["Bounded Ingestion Queue (maxsize=2)"]
    end

    subgraph CoreCV["2. Reusable Computer Vision Pipeline"]
        direction TD
        MagicBytes --> FrameSampler["Adaptive Frame Sampler (5 FPS)"]
        BoundedQueue --> DropPolicy["Drop-Stale-Frame Handler"]
        DropPolicy --> FrameSampler
        FrameSampler --> YOLO["Ultralytics YOLOv8n (CPU Inference)"]
        YOLO --> ByteTrack["ByteTrack (8-State Kalman + IoU Association)"]
        ByteTrack --> Tripwire["Virtual Tripwire Crossing (2D Signed Cross-Product)"]
        Tripwire --> LaneAssign["2D Polygonal Lane Assignment (Ray-Casting & Shoelace Area)"]
        LaneAssign --> FlowEngine["Traffic Metrics & Flow Rate Aggregator"]
    end

    subgraph DataStorage["3. Atomic Relational Persistence"]
        direction TD
        FlowEngine --> DB[("PostgreSQL 16 / SQLite Engine")]
        DB --> T_Videos["videos"]
        DB --> T_Sessions["analysis_sessions"]
        DB --> T_Metrics["traffic_metrics"]
        DB --> T_Lanes["lane_results"]
        DB --> T_Events["crossing_events"]
    end

    subgraph Intelligence["4. Analytics & Decision-Support Engines"]
        direction TD
        DB --> AnomalyEngine["Traffic Incident & Anomaly Detector"]
        DB --> DecisionEngine["Explainable Decision Intelligence Synthesizer"]
        DB --> SignalSim["Webster / HCM Signal Optimization Simulator"]
        DB --> CorridorSim["Emergency Corridor Green-Wave Simulator"]
        DB --> MLForecast["Lag-Engineered ML Forecasting Engine"]
        DB --> ReportGen["ReportLab Vector PDF & CSV Engine"]
    end

    subgraph Presentation["5. Operator Presentation & Telemetry"]
        direction TD
        AnomalyEngine --> Gateway["FastAPI REST & Telemetry Endpoints"]
        DecisionEngine --> Gateway
        SignalSim --> Gateway
        CorridorSim --> Gateway
        MLForecast --> Gateway
        ReportGen --> Gateway
        Gateway --> Nginx["Nginx Reverse Proxy & Static Host"]
        Nginx --> Dashboard["React 18 / TypeScript Dark Command Dashboard"]
    end

    classDef coreSmart fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#ffffff;
    classDef simEngine fill:#4c1d95,stroke:#8b5cf6,stroke-width:2px,color:#ffffff;
    classDef storage fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#ffffff;

    class YOLO,ByteTrack,Tripwire,LaneAssign coreSmart;
    class DecisionEngine,SignalSim,CorridorSim simEngine;
    class DB storage;
```

---

## 🔄 Core Workflow Sequence

*Figure 2: Primary end-to-end request lifecycle and background worker orchestration across analysis execution, persistence, and telemetry.*

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Traffic Operator
    participant UI as React Dark UI
    participant Nginx as Nginx Proxy
    participant API as FastAPI Gateway
    participant JobMgr as AnalysisJobManager
    participant CV as CV Pipeline (YOLO + ByteTrack)
    participant DB as PostgreSQL 16
    participant Engines as Anomaly & Decision Intelligence

    Operator->>UI: Upload traffic video (.mp4) or register RTSP feed
    UI->>Nginx: POST /api/v1/videos/upload
    Nginx->>API: Forward upload payload
    API->>API: Validate container magic bytes & sanitize filename
    API->>DB: Store Video record (provenance_verified = True)
    API-->>UI: 201 Created (video_id, status="uploaded")

    Operator->>UI: Trigger Analysis Job
    UI->>API: POST /api/v1/analysis/jobs {"video_id": "...", "fps": 5}
    API->>JobMgr: submit_job(video_id, config)
    JobMgr->>DB: Persist AnalysisJob (status="QUEUED")
    API-->>UI: 202 Accepted (job_id, status="QUEUED")

    Note over JobMgr,CV: Asynchronous In-Process Worker Pool (max_workers=2)
    JobMgr->>DB: Update AnalysisJob (status="RUNNING")
    JobMgr->>CV: Execute Frame Loop with Cancellation Token

    loop Every Sampled Frame (5 FPS)
        CV->>CV: YOLOv8n vehicle detection & class filtering
        CV->>CV: ByteTrack Kalman state update & track assignment
        CV->>CV: 2D Signed cross-product line crossing evaluation
        CV->>CV: Ray-casting centroid-in-polygon lane assignment
        opt Frame Interval == 5
            CV->>JobMgr: Update progress (frames_processed, total_frames)
            JobMgr->>DB: Update AnalysisJob progress
        end
    end

    CV->>JobMgr: Processing complete (metrics, counts, lane occupancies)
    JobMgr->>DB: ATOMIC COMMIT (AnalysisSession, TrafficMetrics, LaneResults, CrossingEvents)
    JobMgr->>Engines: Trigger post-analysis anomaly & insight evaluation
    Engines->>DB: Persist TrafficAnomalies & TrafficInsights (dedup SHA-256)
    JobMgr->>DB: Update AnalysisJob (status="COMPLETED")

    loop Short Polling Telemetry (1-1.5s)
        UI->>API: GET /api/v1/analysis/jobs/{job_id}
        API->>DB: Query job status
        DB-->>API: Status: COMPLETED
        API-->>UI: 200 OK (status="COMPLETED", session_id)
    end

    UI->>API: GET /api/v1/analysis/{session_id}
    API->>DB: Eager query session details & metrics
    DB-->>API: Session records
    API-->>UI: 200 OK (Full analytical payload with Epistemic Truth Labels)
    UI-->>Operator: Render Dashboard KPIs, Lane Polygons & Decision Advisories
```

---

## 🚦 Key Decision & Logic Flow

*Figure 3: Traffic incident evaluation, severity arbitration, and explainable decision intelligence synthesis flow.*

```mermaid
flowchart TD
    Trigger["Trigger: New Analysis Session Persisted or Live Stream Batch Window"] --> FetchData["Fetch Authoritative Metrics: Flow, Occupancy, Density & Speeds"]
    
    subgraph AnomalyDetection["Statistical Rule Evaluation"]
        direction TD
        FetchData --> EvalCongestion{"Occupancy >= 5 vehicles & Duration >= 20s & Density >= 0.70?"}
        FetchData --> EvalFlowDrop{"Flow Drop >= 50% vs Baseline?"}
        FetchData --> EvalLaneImbalance{"Max/Min Lane Volume Ratio >= 3.0x?"}
        FetchData --> EvalDensitySpike{"Image-Space Density >= 0.00035 veh/px^2?"}

        EvalCongestion -- Yes --> FlagCongestion["Flag Congestion Buildup"]
        EvalFlowDrop -- Yes --> FlagFlow["Flag Flow Degradation"]
        EvalLaneImbalance -- Yes --> FlagImbalance["Flag Asymmetric Lane Bottleneck"]
        EvalDensitySpike -- Yes --> FlagSpike["Flag Localized Density Spike"]
    end

    FlagCongestion --> SeverityRating{"Evaluate Multi-Metric Impact"}
    FlagFlow --> SeverityRating
    FlagImbalance --> SeverityRating
    FlagSpike --> SeverityRating

    SeverityRating -- "Extreme Queue / All Lanes Blocked" --> Critical["Severity: CRITICAL"]
    SeverityRating -- "Multi-Lane Failure / Acute Drop" --> High["Severity: HIGH"]
    SeverityRating -- "Moderate Queuing / Imbalance" --> Medium["Severity: MEDIUM"]
    SeverityRating -- "Minor Slowdown / Underutilization" --> Low["Severity: LOW"]

    subgraph DecisionSynthesis["Explainable Decision Intelligence Layer"]
        direction TD
        Critical --> Deduplication{"Compute dedup_signature SHA256\nExists in DB?"}
        High --> Deduplication
        Medium --> Deduplication
        Low --> Deduplication

        Deduplication -- Yes --> UpdateExisting["Increment recurrence count & update timestamp"]
        Deduplication -- No --> GeneratePackage["Compile Evidence Package:\n- Observed: Empirical camera sensor counts\n- Inferred: Deductive reasoning & confidence rating\n- Limitations: Uncalibrated pixel-space & sample threshold"]
        
        GeneratePackage --> AdvisoryMapping["Map Operational Recommendation:\n(Non-actuating human advisory)"]
        AdvisoryMapping --> CreateInsight["Persist TrafficInsight Record (status = NEW)"]
        UpdateExisting --> PersistDB[("Commit to Database")]
        CreateInsight --> PersistDB
    end

    PersistDB --> AlertDispatch["Push to Command Dashboard & Incident Center"]

    classDef alertCrit fill:#991b1b,stroke:#f87171,stroke-width:2px,color:#ffffff;
    classDef alertHigh fill:#c2410c,stroke:#fb923c,stroke-width:2px,color:#ffffff;
    classDef alertMed fill:#854d0e,stroke:#facc15,stroke-width:2px,color:#ffffff;
    classDef alertLow fill:#1e40af,stroke:#60a5fa,stroke-width:2px,color:#ffffff;
    classDef coreSynth fill:#4c1d95,stroke:#a78bfa,stroke-width:2px,color:#ffffff;

    class Critical alertCrit;
    class High alertHigh;
    class Medium alertMed;
    class Low alertLow;
    class GeneratePackage,AdvisoryMapping,CreateInsight coreSynth;
```

---

## 🗄️ Database & Entity Relationship Model

*Figure 4: Relational schema and entity relationships enforcing audit trails, deduplication constraints, and cascade lifecycles.*

```mermaid
erDiagram
    VIDEOS ||--o{ ANALYSIS_SESSIONS : "analyzed_in"
    CAMERA_SOURCES ||--o{ ANALYSIS_SESSIONS : "monitored_in"
    VIDEOS ||--o{ ANALYSIS_JOBS : "processed_by"
    
    ANALYSIS_SESSIONS ||--o| TRAFFIC_METRICS : "aggregates"
    ANALYSIS_SESSIONS ||--o{ LANE_RESULTS : "segments"
    ANALYSIS_SESSIONS ||--o{ CROSSING_EVENTS : "logs"
    ANALYSIS_SESSIONS ||--o{ TRAFFIC_ANOMALIES : "triggers"
    ANALYSIS_SESSIONS ||--o{ TRAFFIC_INSIGHTS : "synthesizes"
    ANALYSIS_SESSIONS ||--o{ SIGNAL_SIMULATION_RUNS : "seeds"
    ANALYSIS_SESSIONS ||--o{ EMERGENCY_CORRIDOR_SIMULATIONS : "informs"
    ANALYSIS_SESSIONS ||--o{ REPORTS : "exports"
    
    PREDICTION_RUNS ||--o{ PREDICTION_ITEMS : "contains"
    ANALYSIS_SESSIONS ||--o{ PREDICTION_RUNS : "trains"

    VIDEOS {
        string id PK
        string original_filename
        string storage_path
        float duration_seconds
        float fps
        string resolution
        int frame_count
        string source_type
        string source_reference
        boolean provenance_verified
        datetime uploaded_at
    }

    CAMERA_SOURCES {
        string id PK
        string name
        string source_type
        string connection_uri
        int target_fps
        boolean is_active
        datetime created_at
    }

    ANALYSIS_JOBS {
        string id PK
        string video_id FK
        string status
        int total_frames
        int frames_processed
        float processing_fps
        string error_code
        datetime created_at
    }

    ANALYSIS_SESSIONS {
        string id PK
        string video_id FK
        string camera_source_id FK
        string analysis_type
        string status
        float processing_time_ms
        int total_vehicles_detected
        int total_vehicles_counted
        json config_snapshot
        datetime started_at
        datetime completed_at
    }

    TRAFFIC_METRICS {
        string id PK
        string analysis_session_id FK
        float observation_duration_seconds
        int total_volume
        float flow_rate_per_minute
        float flow_rate_per_hour
        boolean is_extrapolated
        json class_distribution
        json direction_distribution
        json time_series_buckets
    }

    LANE_RESULTS {
        string id PK
        string analysis_session_id FK
        string lane_id
        string lane_name
        json polygon_json
        float polygon_area_px2
        int unique_vehicles_count
        int peak_occupancy
        float average_occupancy
        float image_space_density
        float normalized_density_score
    }

    CROSSING_EVENTS {
        string id PK
        string analysis_session_id FK
        int track_id
        string class_name
        string direction
        int frame_index
        float timestamp_seconds
        string line_label
    }

    TRAFFIC_ANOMALIES {
        string id PK
        string session_id FK
        string anomaly_type
        string severity
        string status
        string description
        json metric_snapshot
        datetime created_at
    }

    TRAFFIC_INSIGHTS {
        string id PK
        string session_id FK
        string category
        string severity
        string status
        string dedup_signature
        string observed_evidence
        string inferred_reasoning
        string recommendation
    }

    SIGNAL_SIMULATION_RUNS {
        string id PK
        string analysis_session_id FK
        string intersection_id
        string algorithm_used
        float baseline_avg_delay_seconds
        float optimized_avg_delay_seconds
        float delay_reduction_pct
        string baseline_los
        string optimized_los
        boolean is_simulation
    }

    EMERGENCY_CORRIDOR_SIMULATIONS {
        string id PK
        string session_id FK
        string corridor_id
        string vehicle_type
        float baseline_travel_time_seconds
        float priority_travel_time_seconds
        float travel_time_savings_pct
        float cross_street_extra_delay_sec
        boolean is_simulation
    }

    REPORTS {
        string id PK
        string session_id FK
        string report_type
        string scope
        string file_format
        string file_path
        string sha256_hash
        datetime created_at
    }

    PREDICTION_RUNS {
        string id PK
        string session_id FK
        string model_type
        string data_source
        float mae
        float rmse
        float r2_score
        int horizon_steps
    }

    PREDICTION_ITEMS {
        string id PK
        string prediction_run_id FK
        int step
        float predicted_volume
        float lower_bound
        float upper_bound
        datetime target_timestamp
    }
```

---

## 🧮 Core Algorithms & Mathematical Logic

The platform relies on transparent, deterministic mathematical logic rather than opaque black-box neural networks for all counting, geometric density, and transportation engineering calculations.

### 1. Virtual Tripwire Line Crossing (2D Signed Cross-Product)
To guarantee that vehicles are counted exactly once across user-defined lines, the system tests the vehicle's trajectory segment from frame $t-1$ ($P_{\text{prev}}$) to frame $t$ ($P_{\text{curr}}$) against the virtual tripwire segment defined by line endpoints $A$ and $B$.

The signed 2D cross-product of vector $\vec{AB}$ and vector $\vec{AP}$ is evaluated:
$$\text{Cross}(\vec{AB}, \vec{AP}) = (B_x - A_x)(P_y - A_y) - (B_y - A_y)(P_x - A_x)$$

A valid crossing occurs when the signs of the cross products alternate across consecutive frames:
$$\operatorname{sgn}\left(\text{Cross}(\vec{AB}, \vec{AP}_{\text{prev}})\right) \neq \operatorname{sgn}\left(\text{Cross}(\vec{AB}, \vec{AP}_{\text{curr}})\right)$$

When combined with parametric line intersection parameter testing ($0 \le u \le 1$) and persistent track-ID set deduplication, zero duplicate counts occur even if a vehicle idles on top of the virtual line.

### 2. Polygonal Lane Density & Area (Shoelace Formula)
Lanes are defined as arbitrary 2D polygons with $N$ vertices $(x_0, y_0), \dots, (x_{N-1}, y_{N-1})$. The polygon area $A_{\text{px}^2}$ is calculated deterministically using the Shoelace formula:
$$A_{\text{px}^2} = \frac{1}{2} \left| \sum_{i=0}^{N-1} (x_i y_{i+1} - x_{i+1} y_i) \right| \quad (\text{with } x_N = x_0, y_N = y_0)$$

Tracked vehicle centroids are mapped into polygon lanes via standard Jordan curve ray-casting. Image-space density is defined as:
$$\rho_{\text{image}} = \frac{N_{\text{vehicles}}}{A_{\text{px}^2}} \quad (\text{vehicles/px}^2)$$

Because 2D camera pixel perspective is uncalibrated to physical ground coordinates, normalized scores ($0.0–1.0$) are benchmarked against reference cell areas and accompanied by explicit calibration disclaimers.

### 3. Webster Minimum-Delay Optimization & Lead-Time Preemption
For signal optimization simulations, the system calculates critical approach flow ratios $y_i = q_i / S_i$ (where $q_i$ is demand flow and $S_i$ is approach saturation flow). Total intersection saturation is $Y = \sum y_i$, and total lost time per cycle is $L$.

The minimum-delay optimal cycle length $C_0$ is derived from Webster's formula:
$$C_0 = \frac{1.5L + 5}{1 - Y}$$

Effective green times $g_i$ are allocated proportionally:
$$g_i = \frac{y_i}{Y}(C_0 - L)$$

For emergency vehicle corridors, green-wave preemption incorporates standing queue clearance lead-time:
$$t_{\text{lead}} = Q \times h_d + 2.0\text{s}$$
where $Q$ is the queue length in vehicles and $h_d \approx 2.0\text{s}$ is the average discharge headway per vehicle.

*Figure 5: Webster minimum-delay optimization and dynamic queue clearance lead-time algorithm converging on safety-constrained signal plans.*

```mermaid
flowchart TD
    subgraph Inputs["1. Empirical Approaching Traffic Ingestion"]
        direction TD
        In1["Approach Flow Demands: q_i (veh/hr)"]
        In2["Saturation Flow Rates: S_i (veh/hr green)"]
        In3["Lost Time per Phase: l_i (seconds)"]
        In4["Standing Queue Length: Q (vehicles)"]
        In5["Discharge Headway: h_d (approx 2.0s/veh)"]
    end

    subgraph Computation["2. Mathematical Traffic Engineering Engine"]
        direction TD
        In1 & In2 --> FlowRatio["Approach Flow Ratio:\ny_i = q_i / S_i"]
        FlowRatio --> SumRatios["Intersection Saturation:\nY = sum(y_i)"]
        In3 --> TotalLost["Total Lost Time:\nL = sum(l_i) + R_all"]
        
        SumRatios & TotalLost --> WebsterEq["Webster Minimum-Delay Optimal Cycle:\nC_0 = (1.5L + 5) / (1 - Y)"]
        
        WebsterEq & FlowRatio --> GreenSplit["Effective Green Split:\ng_i = (y_i / Y) * (C_0 - L)"]
        
        In4 & In5 --> LeadTime["Emergency Queue Clearance Lead-Time:\nt_lead = Q * h_d + 2.0s"]
    end

    subgraph SafetyConstraints["3. Strict Safety Invariants & Bound Clamping"]
        direction TD
        GreenSplit --> SafetyCheck{"Evaluate Safety Bounds"}
        SafetyCheck --> CheckMinGreen["g_min >= 7.0s"]
        SafetyCheck --> CheckYellow["y_clearance >= 3.0s"]
        SafetyCheck --> CheckAllRed["r_clearance >= 1.0s"]
        SafetyCheck --> CheckMaxHold["max_priority_hold <= 80.0s"]
    end

    subgraph Outputs["4. Grounded Decision Support Output"]
        direction TD
        CheckMinGreen & CheckYellow & CheckAllRed & CheckMaxHold --> Plan["Optimized Signal Timing Plan & LOS A-F Evaluation"]
        LeadTime --> Preemption["Coordinated Dynamic Green-Wave Window"]
    end

    classDef calc fill:#1e3a8a,stroke:#3b82f6,stroke-width:2px,color:#ffffff;
    classDef safety fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#ffffff;
    classDef output fill:#4c1d95,stroke:#8b5cf6,stroke-width:2px,color:#ffffff;

    class FlowRatio,SumRatios,WebsterEq,GreenSplit,LeadTime calc;
    class SafetyCheck,CheckMinGreen,CheckYellow,CheckAllRed,CheckMaxHold safety;
    class Plan,Preemption output;
```

---

## 🛡️ Error Handling & API Codes

The backend implements centralized exception handling (`app.core.exceptions`). Internal stack traces and raw server paths are never exposed to clients. Every error response adheres to an immutable envelope:
```json
{"error": {"code": "...", "message": "..."}}
```

| Error Code | HTTP Status | Trigger Condition / Description |
|---|---|---|
| `invalid_filename` | 400 Bad Request | Empty filename, control characters, or malicious path traversal sequences (`../`). |
| `invalid_extension` | 400 Bad Request | Uploaded file extension is not permitted (must be `.mp4`, `.avi`, or `.mov`). |
| `invalid_video_container` | 400 Bad Request | File magic bytes fail ISO BMFF / RIFF container validation (rejects renamed binaries). |
| `empty_file` | 400 Bad Request | Uploaded file contains 0 bytes. |
| `insufficient_data_for_prediction`| 400 Bad Request | Verified real-world observations ($N < 20$) are below the required ML training threshold. |
| `video_not_found` | 404 Not Found | Referenced video UUID does not exist in the database or storage. |
| `session_not_found` | 404 Not Found | Referenced analysis session UUID does not exist. |
| `camera_source_not_found` | 404 Not Found | Specified camera source UUID does not exist. |
| `report_not_found` | 404 Not Found | Requested PDF or CSV report file does not exist on disk or in the registry. |
| `duplicate_active_job` | 409 Conflict | An analysis job is already `QUEUED` or `RUNNING` for the specified video ID. |
| `camera_already_running` | 409 Conflict | A live worker thread is already actively monitoring the requested camera source. |
| `file_too_large` | 413 Payload Too Large | Uploaded file size exceeds `MAX_UPLOAD_SIZE_MB` (500 MB). |
| `validation_error` | 422 Unprocessable Entity| Request payload failed Pydantic schema validation (e.g. malformed JSON or out-of-range bounds). |
| `max_jobs_exceeded` | 429 Too Many Requests | Background worker pool is saturated at capacity (`MAX_CONCURRENT_ANALYSIS_JOBS`). |
| `max_live_streams_exceeded` | 429 Too Many Requests | Active camera streams have reached concurrency limit (`MAX_LIVE_STREAMS`). |
| `internal_error` | 500 Internal Error | Unhandled server exception. Sanitized generic error returned; full trace logged server-side. |

---

## 🧪 Testing & Verification

The platform maintains automated test suites across both backend and frontend layers with zero regressions.

```bash
# 1. Run complete backend unit and integration test suite (220 tests)
python -m pytest backend/tests -v

# 2. Run Phase 21 Live Monitoring verification script (16 automated checks)
python scripts/verify_phase21_live_monitoring.py

# 3. Run Phase 20 Production Readiness & Packaging verification script
python scripts/verify_phase20_production_readiness.py

# 4. Run individual subsystem regression scripts
python scripts/verify_phase10_database.py
python scripts/verify_phase15_anomaly_detection.py
python scripts/verify_phase17_job_orchestration.py
python scripts/verify_phase18_decision_intelligence.py
python scripts/verify_phase19_reporting.py

# 5. Run frontend TypeScript type checking and production build
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

---

## 🧭 Design Philosophy

1. **Epistemic Honesty over Completeness-Theater**  
   The platform never invents data to make a dashboard look busy. Sensor counts are marked `OBSERVED`, mathematical simulations are marked `SIMULATED`, and ML predictions are explicitly marked `UNAVAILABLE` when historical sample thresholds ($N < 20$) are not met.
2. **Determinism & Mathematical Verifiability**  
   Counting, density calculation, and signal timing rely on proven computational geometry (cross-product orientation, Shoelace area) and established transportation engineering models (Webster delay equations, HCM Level of Service). Given the same inputs, the system always produces the exact same results.
3. **Modular Monolith over Microservice Sprawl**  
   All services run within a cohesive, single-node architecture with clear internal boundaries. Ingestion, tracking, persistence, simulation, and reporting run as decoupled Python modules without requiring Kafka clusters, Redis brokers, or distributed coordination overhead.
4. **Edge-First Efficiency on Standard Hardware**  
   Computer vision models and tracking algorithms are optimized for lightweight CPU execution. The platform operates reliably on standard municipal edge boxes and modest cloud instances without requiring specialized GPU accelerators.
5. **Zero-Broker Simplicity & Resource Safety**  
   Real-time video ingestion employs bounded queues (`maxsize=2`) with systematic frame dropping to prevent memory bloat and latency spikes. Client telemetry uses robust short HTTP polling, avoiding fragile WebSocket state management.

---

## 🗺️ Near-Term Roadmap

- [ ] **Multi-Camera Spatio-Temporal Vehicle Re-Identification (ReID):** Correlate vehicle tracks across adjacent intersection cameras using appearance feature embeddings without plate-logging privacy risks.
- [ ] **Hardware Acceleration via ONNX Runtime & TensorRT:** Provide optional pluggable inference backends for NVIDIA Jetson and Intel OpenVINO edge hardware.
- [ ] **Standard Transportation Protocol Bridging:** Export simulated signal optimization plans in standard NTCIP 1202 and SPaT/MAP V2X message formats for direct integration with traffic controller testbeds.
- [ ] **Enterprise Role-Based Access Control (RBAC):** Implement OAuth2 / OpenID Connect authentication with operator vs auditor permission tiers.
- [ ] **Weather & Lighting Degradation Heuristics:** Automatically flag reduced CV confidence during heavy precipitation, fog, or low-light night conditions.

---

## 👥 Authors & Contributors

- **Akhil** — *Lead Architect & Systems Engineer* — [GitHub](https://github.com/Akhil-Bansal17)
- Open source community contributions and traffic engineering advisors.

---

## 📄 License & Provenance

- **Software License:** MIT License. See [LICENSE](LICENSE) for full details.
- **Model Weights:** Ultralytics YOLOv8n is governed by the Ultralytics AGPL-3.0 / Commercial License.
- **Real-World Test Data Provenance:** Genuine traffic video recordings utilized for pipeline validation are documented under permissive MIT / CC-BY open-source licenses in `data_science/datasets/real_traffic/`.

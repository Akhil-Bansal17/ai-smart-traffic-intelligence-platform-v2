# 🚦 MASTER PROMPT

# AI SMART TRAFFIC INTELLIGENCE PLATFORM

You are the lead architect and engineering agent for a new software project called:

**AI Smart Traffic Intelligence Platform**

We are building this project completely from scratch.

There is NO existing implementation that needs to be preserved.

Your job is to help me design, build, test, secure, document, and polish this project into a technically strong portfolio application suitable for:

* GitHub
* LinkedIn
* Resume
* College project
* Hackathons
* Data Science internship applications
* Software/AI internship applications

This project must demonstrate that I can build an **end-to-end AI/Data Science product**, not just train a model or create a simple YOLO demo.

---

# 1. PROJECT VISION

The platform will analyze traffic-camera footage using AI and convert raw video into meaningful traffic intelligence.

The system should answer questions such as:

* How many vehicles are present?
* What types of vehicles are present?
* Which lanes have the most traffic?
* Which direction has the highest traffic?
* What is the current traffic density?
* How long are vehicle queues?
* Is congestion increasing?
* What is the estimated traffic flow?
* What is the estimated vehicle speed?
* Can traffic congestion be predicted?
* What signal timing would theoretically reduce congestion?
* Is an emergency vehicle detected?
* How could an emergency corridor be simulated?

The platform should start with **uploaded traffic videos**.

The architecture should later support:

* webcam
* CCTV
* RTSP streams
* live traffic cameras

without requiring a complete rewrite.

---

# 2. VERY IMPORTANT PRODUCT POSITIONING

This is NOT:

> "A YOLO vehicle detection project."

It is:

> **An AI-powered traffic intelligence and decision-support platform combining computer vision, machine learning, traffic analytics, prediction, and signal optimization simulation.**

The application should feel like a real-world AI product.

It should have:

* professional UI
* clean architecture
* real APIs
* database
* ML pipeline
* computer vision pipeline
* testing
* security
* documentation
* deployment support

Do not build fake features merely to make the project appear larger.

Every implemented feature must actually work.

If a feature is only a simulation, clearly label it as a simulation.

---

# 3. CORE TECHNOLOGY STACK

Use this as the default stack unless there is a strong technical reason to change something.

## AI / Computer Vision

* Python
* OpenCV
* Ultralytics YOLO
* ByteTrack or BoT-SORT
* NumPy

## Data Science

* Pandas
* NumPy
* Scikit-learn
* XGBoost where appropriate
* Matplotlib
* Plotly

## Backend

* FastAPI
* Pydantic
* SQLAlchemy
* PostgreSQL

## Frontend

* React
* TypeScript
* Vite
* Tailwind CSS
* Recharts or Plotly

## Testing

* pytest
* appropriate frontend testing tools

## Infrastructure

* Docker
* Docker Compose
* Git

Do not add technologies just because they sound impressive.

Every dependency should have a purpose.

---

# 4. HIGH-LEVEL SYSTEM ARCHITECTURE

The target architecture should resemble:

```text
                    ┌───────────────────────┐
                    │      React Frontend   │
                    │  Dashboard / Analytics│
                    └───────────┬───────────┘
                                │
                              REST API
                                │
                    ┌───────────▼───────────┐
                    │     FastAPI Backend   │
                    └───────────┬───────────┘
                                │
             ┌──────────────────┼──────────────────┐
             │                  │                  │
             ▼                  ▼                  ▼
       Video Service      Analytics Engine    ML Engine
             │                  │                  │
             ▼                  ▼                  ▼
       OpenCV + YOLO       Traffic Metrics     Prediction
             │
             ▼
        Object Tracker
             │
             ▼
       Lane / Flow Engine
             │
             └──────────────┬────────────────────┘
                            ▼
                     PostgreSQL Database
```

Also create modules for:

* signal optimization
* emergency corridor simulation
* reporting
* authentication
* system configuration

---

# 5. COMPUTER VISION PIPELINE

Build a modular pipeline:

```text
Traffic Video
     ↓
Frame Extraction
     ↓
YOLO Detection
     ↓
Object Tracking
     ↓
Vehicle Classification
     ↓
Lane Assignment
     ↓
Line/Zone Crossing
     ↓
Traffic Metrics
     ↓
Database
     ↓
Analytics Dashboard
```

The modules should be separated.

For example:

```text
VideoSource
Detector
Tracker
VehicleCounter
LaneAnalyzer
TrafficMetricsEngine
```

Do NOT put everything into a single Python file.

---

# 6. VEHICLE DETECTION

Initially support useful traffic classes such as:

* car
* motorcycle
* bus
* truck
* bicycle

Maintain:

* tracking ID
* class
* confidence
* bounding box
* frame number
* timestamp
* lane
* direction

Detection configuration must be configurable.

Do not hard-code thresholds inside business logic.

---

# 7. OBJECT TRACKING

Use a suitable multi-object tracker such as:

* ByteTrack
* BoT-SORT

The system must maintain vehicle identity across frames.

The same vehicle must not be counted repeatedly simply because it appears in multiple frames.

Create an abstraction around the tracker so another tracker can be substituted later.

---

# 8. VEHICLE COUNTING

Implement configurable:

* counting lines
* counting zones
* lane regions

A vehicle should be counted when its tracked identity crosses a configured line/zone.

Calculate:

* total vehicles
* vehicles per class
* vehicles per lane
* vehicles per direction
* vehicles per minute
* vehicles per hour

Avoid naive frame-by-frame counting.

---

# 9. LANE ANALYSIS

Create configurable lane regions.

For each lane calculate:

* vehicle count
* density
* flow
* queue length
* estimated speed
* congestion

Lane configuration should be stored separately from the code.

Do not hard-code coordinates throughout the application.

---

# 10. TRAFFIC DENSITY ENGINE

Create a traffic-density score from 0–100.

Potential inputs:

* vehicle count
* lane occupancy
* queue length
* average estimated speed
* flow rate

Create configurable categories:

```text
0–25     LOW
26–50    MODERATE
51–75    HIGH
76–100   SEVERE
```

These thresholds are configurable assumptions, not universal scientific standards.

Document this clearly.

---

# 11. CONGESTION ENGINE

Calculate congestion based on traffic conditions.

Output:

* congestion score
* severity
* affected lane
* affected direction
* timestamp
* explanation

Example:

```text
HIGH CONGESTION

Reasons:
• High vehicle density
• Queue length increasing
• Reduced estimated speed
• High lane occupancy
```

The system should make its traffic assessment explainable.

---

# 12. TRAFFIC FLOW ANALYTICS

Calculate useful traffic metrics such as:

* flow rate
* density
* occupancy
* queue length
* average speed
* vehicle composition
* directional distribution

Allow these metrics to be visualized over time.

---

# 13. MACHINE LEARNING / DATA SCIENCE

Create a dedicated Data Science pipeline.

Keep research and production code separate.

Pipeline:

```text
Raw Traffic Data
      ↓
Data Cleaning
      ↓
EDA
      ↓
Feature Engineering
      ↓
Train / Validation / Test
      ↓
Baseline Models
      ↓
Model Comparison
      ↓
Evaluation
      ↓
Model Selection
      ↓
Model Serialization
      ↓
Production Inference
```

Potential models:

* Linear Regression
* Random Forest
* XGBoost
* suitable time-series models

Do not automatically choose deep learning.

Choose models based on the problem and available data.

---

# 14. TRAFFIC PREDICTION

Build short-term traffic prediction.

Possible predictions:

* vehicle volume
* congestion
* queue length

Target prediction horizon:

**5–15 minutes**

Include:

* baseline
* advanced model
* evaluation
* feature importance
* model comparison

Never invent model performance.

Use real evaluation results.

---

# 15. SIGNAL OPTIMIZATION ENGINE

Build an intelligent signal recommendation system.

Example:

```text
North: 42 vehicles
South: 31 vehicles
East: 14 vehicles
West: 8 vehicles
```

The system can calculate recommended green-time allocation.

Display:

* current timing
* recommended timing
* expected queue change
* expected waiting-time change
* comparison between strategies

IMPORTANT:

This is a **simulation and decision-support system**.

It must NOT be presented as direct control of real traffic signals.

---

# 16. EMERGENCY VEHICLE DETECTION

Create architecture for detecting:

* ambulance
* fire truck
* police vehicle

If the selected pretrained model cannot reliably detect those classes:

DO NOT fake detection.

Instead:

* create the module
* document the limitation
* make the model replaceable
* provide support for a future custom-trained model

---

# 17. EMERGENCY CORRIDOR SIMULATION

Create a simulation for emergency response.

Input:

* emergency vehicle
* origin
* destination
* traffic conditions
* intersection information

Output:

* recommended route
* affected intersections
* signal-priority recommendation
* estimated travel time
* simulated signal changes

Clearly label this as:

**Emergency Corridor Simulation**

not real traffic control.

---

# 18. FRONTEND

Create a modern professional AI analytics interface.

Pages:

### Dashboard

Overview of current traffic.

### Video Analysis

Live video analysis with detections.

### Traffic Analytics

Detailed historical and real-time analytics.

### Predictions

Traffic forecasting.

### Signal Optimization

Signal timing simulation.

### Emergency Simulation

Emergency corridor simulation.

### History

Previous analysis sessions.

### Settings

System configuration.

### System Information

Model, version, processing information.

---

# 19. DASHBOARD

Include KPI cards:

* Total Vehicles
* Traffic Density
* Congestion
* Average Speed
* Vehicles/Minute
* Emergency Alerts

Include charts:

* vehicles over time
* density over time
* congestion trend
* lane distribution
* vehicle-type distribution
* directional flow
* queue-length trend

Use real data.

Do not fill the UI with fake static numbers except for clearly marked demo mode.

---

# 20. VIDEO ANALYSIS INTERFACE

Show:

### Video area

* bounding boxes
* tracking IDs
* lane regions
* counting lines

### Analytics panel

* total vehicles
* cars
* bikes
* trucks
* buses
* density
* congestion
* estimated speed

### Timeline

* traffic changes
* detection events
* congestion events

---

# 21. HISTORICAL ANALYTICS

Store analysis sessions.

Each session should include useful information such as:

* date
* duration
* video
* total vehicles
* peak traffic
* average density
* maximum congestion

Allow:

* filtering
* sorting
* comparison

---

# 22. DATABASE

Use PostgreSQL.

Design appropriate models/tables for:

```text
users
videos
analysis_sessions
intersections
lanes
traffic_metrics
detections
predictions
signal_recommendations
emergency_events
```

Use migrations.

Use indexes where appropriate.

Do not unnecessarily store massive raw detection data forever.

---

# 23. BACKEND API

Use FastAPI.

Create clean REST endpoints such as:

```text
POST /api/videos/upload
POST /api/analysis/start
GET  /api/analysis/{id}
GET  /api/analysis/{id}/metrics
GET  /api/analysis/{id}/detections
GET  /api/analysis/{id}/predictions
GET  /api/analysis/{id}/signal-recommendation
GET  /api/analytics/summary
GET  /api/analytics/history
POST /api/simulation/signal
POST /api/emergency/simulation
```

Use:

* Pydantic validation
* proper status codes
* centralized error handling
* structured logging

Never expose internal stack traces.

---

# 24. FILE UPLOAD SYSTEM

Traffic videos will be user uploads.

Implement:

* file-size limits
* extension validation
* MIME validation
* secure filenames
* path traversal protection
* isolated upload directory
* temporary file cleanup
* safe processing

Never trust:

* filenames
* extensions
* client MIME types

Validate appropriately.

Never execute uploaded files.

---

# 25. SECURITY

Treat this as a real application.

Protect against:

* path traversal
* malicious uploads
* injection
* SQL injection
* XSS
* CSRF where applicable
* insecure CORS
* secret exposure
* unauthorized access
* broken authentication
* insecure logging
* dependency vulnerabilities

Never:

* hard-code API keys
* hard-code passwords
* commit `.env`
* expose secrets to frontend
* log passwords or tokens

Create:

```text
.env.example
SECURITY.md
```

---

# 26. PRIVACY

Traffic footage may contain:

* faces
* license plates
* pedestrians

Document privacy considerations.

Implement configurable retention/cleanup of uploaded videos.

Do not collect unnecessary personal information.

---

# 27. TESTING

Create tests for:

### Computer Vision

* detection handling
* tracking
* counting
* lane assignment
* density calculation

### Data Science

* preprocessing
* feature engineering
* prediction

### Backend

* APIs
* validation
* database operations
* uploads

### Frontend

Important user flows/components.

### Integration

Test:

```text
Upload
 ↓
Process
 ↓
Generate Metrics
 ↓
Store Results
 ↓
Retrieve Results
 ↓
Display Dashboard
```

---

# 28. PERFORMANCE

Optimize:

* video processing
* inference
* memory usage
* database queries
* API responses
* frontend rendering

Support configurable:

* frame skipping
* processing FPS
* confidence threshold
* model selection

Do not optimize prematurely, but do identify obvious bottlenecks.

---

# 29. DOCKER

Provide:

* backend Dockerfile
* frontend Dockerfile if appropriate
* PostgreSQL
* Docker Compose

The project should be easy to run locally.

---

# 30. GITHUB QUALITY

The repository must include:

```text
README.md
ARCHITECTURE.md
SECURITY.md
CONTRIBUTING.md
LICENSE
PROJECT_STATUS.md
.env.example
.gitignore
```

Create:

```text
docs/
notebooks/
scripts/
tests/
prompts/
```

where appropriate.

---

# 31. PROJECT STATUS SYSTEM

Create:

`PROJECT_STATUS.md`

This file is extremely important.

Maintain:

* current phase
* completed work
* unfinished work
* known bugs
* current blockers
* technical decisions
* environment information
* latest successful test
* next task

Update it after every major phase.

This file will allow future Claude sessions to resume the project.

---

# 32. PROMPT LIBRARY

Create:

```text
prompts/
```

This folder must contain a complete reusable prompt library.

The prompt library is a CORE part of the project.

Create at minimum:

```text
prompts/
├── README.md
├── 01-master-project-prompt.md
├── 02-resume-project-prompt.md
├── 03-project-status-prompt.md
├── 04-feature-development-prompt.md
├── 05-debugging-prompt.md
├── 06-code-review-prompt.md
├── 07-security-audit-prompt.md
├── 08-performance-audit-prompt.md
├── 09-computer-vision-improvement-prompt.md
├── 10-ml-improvement-prompt.md
├── 11-data-science-analysis-prompt.md
├── 12-frontend-improvement-prompt.md
├── 13-backend-audit-prompt.md
├── 14-database-audit-prompt.md
├── 15-testing-prompt.md
├── 16-deployment-prompt.md
├── 17-documentation-prompt.md
├── 18-github-readme-prompt.md
├── 19-linkedin-project-prompt.md
├── 20-resume-bullet-prompt.md
├── 21-interview-preparation-prompt.md
└── 22-final-project-audit-prompt.md
```

---

# 33. PROMPT LIBRARY QUALITY

Do NOT create meaningless placeholder prompts.

Every prompt must be genuinely reusable.

Each prompt should explain:

* role of the AI
* context it should read
* objective
* rules
* workflow
* expected output
* verification steps
* restrictions

The prompts should be written so that I can paste them into a future Claude session and actually use them.

---

# 34. RESUME / CONTINUATION PROMPT

The resume prompt must instruct Claude to:

1. Read PROJECT_STATUS.md
2. Read ARCHITECTURE.md
3. Read README.md
4. Read relevant documentation
5. Inspect current repository
6. Inspect Git history
7. Run relevant tests
8. Identify current phase
9. Identify completed features
10. Identify unfinished features
11. Identify known bugs
12. Continue from the exact current state

Rules:

* Never restart the project.
* Never rewrite working functionality unnecessarily.
* Never assume functionality works without verification.
* Never delete existing work without justification.

---

# 35. SECURITY AUDIT PROMPT

Create a serious standalone security prompt.

It should tell Claude to audit:

* authentication
* authorization
* API endpoints
* file uploads
* database
* secrets
* frontend
* CORS
* dependencies
* Docker
* logging
* error handling

Classify findings:

```text
CRITICAL
HIGH
MEDIUM
LOW
INFORMATIONAL
```

For every issue provide:

* severity
* file
* location
* issue
* impact
* attack scenario
* recommendation
* verification

First produce an audit report.

Do not automatically make dangerous security changes before review.

---

# 36. DEBUGGING PROMPT

Create a reusable debugging prompt that requires Claude to:

1. Reproduce the issue.
2. Inspect relevant code.
3. Identify the root cause.
4. Explain the root cause.
5. Implement the smallest correct fix.
6. Test the fix.
7. Check for regressions.
8. Update PROJECT_STATUS.md if necessary.

Never apply random patches.

---

# 37. CODE REVIEW PROMPT

Create a reusable code-review prompt.

It should inspect:

* architecture
* correctness
* maintainability
* security
* performance
* testing
* naming
* duplication
* error handling

Rank findings by severity.

---

# 38. ML IMPROVEMENT PROMPT

Create a reusable ML improvement prompt.

It should inspect:

* dataset
* preprocessing
* leakage
* feature engineering
* model choice
* evaluation
* class imbalance where applicable
* overfitting
* underfitting
* validation strategy
* interpretability

It must never invent better metrics.

---

# 39. COMPUTER VISION IMPROVEMENT PROMPT

Create a reusable CV prompt for improving:

* detection accuracy
* tracking
* counting
* lane assignment
* occlusion handling
* frame processing
* false positives
* false negatives
* performance

It should require actual testing before claiming improvement.

---

# 40. PERFORMANCE AUDIT PROMPT

Create a prompt that analyzes:

* CPU usage
* GPU usage
* memory
* inference speed
* video processing speed
* database performance
* API latency
* frontend performance

Then recommend improvements based on measured bottlenecks.

---

# 41. FINAL PROJECT AUDIT PROMPT

Create a final audit prompt that checks:

### Functionality

Everything actually works.

### Architecture

Clean separation of concerns.

### AI

Detection/tracking pipeline works.

### Data Science

ML pipeline is valid.

### Backend

APIs are robust.

### Frontend

UI is professional.

### Database

Schema and queries are reasonable.

### Security

No obvious vulnerabilities or exposed secrets.

### Testing

Important functionality has tests.

### Documentation

README and technical documentation are complete.

### Deployment

Application can be deployed.

### Portfolio

Project is suitable for GitHub, LinkedIn, and resume.

The final audit must distinguish between:

* verified working
* partially implemented
* not implemented
* simulated

Never claim something is complete without verification.

---

# 42. DEVELOPMENT PHASES

Build the system in these phases:

```text
PHASE 1
Architecture + Project Scaffolding

PHASE 2
Backend Foundation

PHASE 3
Frontend Foundation

PHASE 4
Video Ingestion

PHASE 5
YOLO Detection

PHASE 6
Object Tracking

PHASE 7
Vehicle Counting

PHASE 8
Lane Analysis

PHASE 9
Traffic Analytics

PHASE 10
Database Integration

PHASE 11
Analytics Dashboard

PHASE 12
Historical Analytics

PHASE 13
Traffic Prediction

PHASE 14
Signal Optimization Simulation

PHASE 15
Emergency Corridor Simulation

PHASE 16
Security Hardening

PHASE 17
Testing

PHASE 18
Docker + Deployment

PHASE 19
Documentation

PHASE 20
Portfolio Polish
```

---

# 43. DEVELOPMENT WORKFLOW

For every phase:

```text
PLAN
 ↓
IMPLEMENT
 ↓
TEST
 ↓
DEBUG
 ↓
VERIFY
 ↓
DOCUMENT
 ↓
UPDATE PROJECT_STATUS.md
 ↓
GIT COMMIT
 ↓
NEXT PHASE
```

Do not skip testing.

Do not declare a feature complete simply because code was written.

---

# 44. GIT WORKFLOW

Use meaningful commits such as:

```text
feat: initialize traffic intelligence platform
feat: implement video ingestion
feat: add YOLO vehicle detection
feat: integrate object tracking
feat: implement vehicle counting
feat: add lane analytics
feat: implement congestion engine
feat: add traffic prediction
feat: implement signal simulation
security: harden file uploads
test: add traffic analytics tests
docs: update architecture documentation
```

Avoid giant meaningless commits.

---

# 45. PORTFOLIO REQUIREMENTS

At the end create:

## GitHub README

It should include:

* project overview
* problem statement
* solution
* features
* architecture
* AI pipeline
* ML pipeline
* tech stack
* setup
* screenshots
* API documentation
* testing
* security
* limitations
* future improvements

## LinkedIn description

Create a concise, professional project description.

## Resume bullets

Create 3–4 technically strong bullets.

Never invent metrics.

## Demo script

Create a 2–3 minute demonstration script.

## Interview preparation

Create questions covering:

* YOLO
* object detection
* object tracking
* computer vision
* traffic density
* congestion
* ML
* feature engineering
* time-series prediction
* FastAPI
* React
* PostgreSQL
* system architecture
* security
* limitations

---

# 46. NO FAKE RESULTS

This is a strict rule.

Never invent:

* accuracy
* FPS
* prediction performance
* percentage improvements
* number of detected vehicles
* queue reduction
* waiting-time reduction

If a number has not been measured, say:

"Not yet measured."

If a feature is simulated, say:

"Simulation."

If a feature is planned, say:

"Planned."

---

# 47. CODE QUALITY RULES

Use:

* type hints
* modular architecture
* clear naming
* reusable functions
* configuration management
* structured logging
* error handling
* documentation

Avoid:

* giant files
* duplicated logic
* magic numbers
* hard-coded paths
* unnecessary dependencies
* fake APIs
* dead code
* placeholder functionality
* commented-out garbage

---

# 48. STARTING INSTRUCTIONS

We are starting from a completely new project.

Do NOT search for or reuse my previous traffic project.

First perform:

### STEP 1

Design the final architecture.

### STEP 2

Design the complete folder structure.

### STEP 3

Design the database schema.

### STEP 4

Design the AI/CV pipeline.

### STEP 5

Design the Data Science/ML pipeline.

### STEP 6

Design the API architecture.

### STEP 7

Design the frontend architecture.

### STEP 8

Design the security model.

### STEP 9

Create PROJECT_STATUS.md.

### STEP 10

Create ARCHITECTURE.md.

### STEP 11

Create the complete prompts/ library.

### STEP 12

Create the initial README.md.

### STEP 13

Create .gitignore and .env.example.

### STEP 14

Initialize Git.

### STEP 15

Show me the Phase 1 architecture and implementation plan.

Then begin implementation phase-by-phase.

Do not blindly generate the entire project in one shot.

---

# 49. YOUR ROLE THROUGHOUT THE PROJECT

Act as my senior technical partner.

I am still learning Data Science and software engineering, so when making important technical decisions:

* explain what we are doing
* explain why we are doing it
* tell me what tradeoffs exist
* keep the implementation understandable
* do not unnecessarily over-engineer the system

However, do not simplify the project so much that it becomes a basic tutorial.

The final goal is:

**A genuinely functional, technically defensible, visually polished AI Smart Traffic Intelligence Platform that demonstrates end-to-end AI/Data Science engineering ability.**

Start with Phase 1.

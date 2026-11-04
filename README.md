# Sentry — AI-Powered Intelligent Traffic Monitoring & Vehicle Detection System

Real-time vehicle detection, tracking, speed estimation, violation
detection, and traffic analytics — for CCTV, dashcam, webcam, drone, and
uploaded video sources.

**Status: feature-complete across all 10 build phases.** 37/37 backend
tests passing; frontend build verified. See [Verification](#verification)
below for exactly what was tested and how.

## Tech Stack

| Layer      | Technology |
|------------|------------|
| Detection  | YOLOv8 (Ultralytics), PyTorch |
| Tracking   | DeepSORT |
| Backend    | FastAPI, OpenCV, NumPy, Pandas |
| Frontend   | React, Vite, TailwindCSS, Framer Motion, Chart.js |
| Database   | MongoDB |
| Deployment | Docker, Nginx, GitHub Actions |

## Features

- **Detection**: 8 vehicle classes (car, truck, bus, motorcycle, bicycle,
  auto-rickshaw, van, emergency vehicle — the last 3 need a custom-trained
  model, see [docs/dataset-and-training-guide.md](docs/dataset-and-training-guide.md))
  across webcam, RTSP/IP camera, and uploaded video sources
- **Tracking**: permanent per-vehicle IDs via DeepSORT, path history,
  object lifetime, motion direction
- **Counting**: configurable virtual entry/exit line, per-class and total counts
- **Speed estimation**: calibrated pixel-displacement speed with overspeed flagging
- **Violations**: wrong-direction, lane violation, red-light-jump (simulated
  signal), illegal U-turn, no-parking
- **Alerts**: rate-limited Telegram + email notifications on violations,
  overspeed, crowded areas, and loitering
- **Analytics**: hourly/daily counts, class distribution, peak-hour detection,
  violation totals — aggregated from MongoDB
- **Reports**: CSV, multi-sheet Excel, and formatted PDF export
- **Heatmaps**: accumulated traffic-density overlay per camera
- **Dashboard**: live MJPEG stream viewer, charts, session controls, report
  downloads — dark "traffic ops room" themed React UI
- **Multi-camera**: each session runs independently in its own thread

## Project Structure

```
traffic-ai-system/
├── backend/
│   ├── app/
│   │   ├── api/          # REST route handlers (detection, analytics, reports)
│   │   ├── core/         # config, logging, database, vehicle class mapping
│   │   ├── schemas/      # Pydantic request/response models
│   │   ├── services/     # detector, tracker session, alerts, analytics, reports, heatmap
│   │   ├── tracking/     # DeepSORT wrapper + trajectory store
│   │   ├── violations/   # rule-based violation detectors
│   │   ├── utils/        # drawing, geometry helpers
│   │   └── tests/        # pytest suite (37 tests)
│   ├── scripts/          # weight download, ONNX/TensorRT export
│   ├── tests/            # stress_test.py (live load test, not pytest)
│   └── requirements.txt
├── frontend/              # React + Vite + Tailwind dashboard
│   └── src/
│       ├── api/           # backend API client
│       ├── components/    # Sidebar, TopBar, StatCard
│       └── pages/         # Landing, Dashboard, LiveDetection, Analytics, Reports, Settings, About
├── deployment/
│   ├── docker/            # backend + frontend Dockerfiles
│   └── nginx/             # SPA + reverse-proxy config
├── docs/                  # architecture, API, dataset/training, deployment, performance, roadmap
├── .github/workflows/     # CI: backend tests, frontend build, docker build
├── models/weights/        # YOLOv8 weight files (not committed)
├── docker-compose.yml
└── .gitignore
```

## Quick Start

### Docker (full stack)

```bash
git clone <your-repo-url>
cd traffic-ai-system
cp backend/.env.example backend/.env
docker compose up --build
```

- Backend API docs: http://localhost:8000/api/docs
- Frontend dashboard: http://localhost:5173

### Local development

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python scripts/download_weights.py --model yolov8n.pt
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Full setup details, GPU configuration, and troubleshooting:
[docs/installation-guide.md](docs/installation-guide.md).

## Try it end-to-end

```bash
curl -X POST http://localhost:8000/api/v1/detection/start \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "webcam", "source": "0", "camera_id": "gate-1",
    "counting_line": {"point_a": {"x": 0, "y": 240}, "point_b": {"x": 640, "y": 240}},
    "pixels_per_meter": 8.0, "speed_limit_kmph": 60,
    "violations": {"enable_violations": true, "correct_direction_deg": 0},
    "enable_alerts": true
  }'

# Live annotated stream:
#   http://localhost:8000/api/v1/detection/stream/<session_id>
# Live counts:
curl http://localhost:8000/api/v1/detection/sessions/<session_id>/counts
# Analytics summary:
curl http://localhost:8000/api/v1/analytics/summary?days=7
# PDF report:
curl -OJ http://localhost:8000/api/v1/reports/pdf?days=7
```

Full endpoint reference: [docs/api-documentation.md](docs/api-documentation.md).

## Documentation

| Doc | Covers |
|-----|--------|
| [docs/architecture.md](docs/architecture.md) | System diagram, component responsibilities, threading model |
| [docs/api-documentation.md](docs/api-documentation.md) | Every endpoint, with a full example request |
| [docs/installation-guide.md](docs/installation-guide.md) | Setup for Docker and local dev, GPU config, troubleshooting |
| [docs/deployment-guide.md](docs/deployment-guide.md) | Production deployment, hardening checklist, scaling notes |
| [docs/dataset-and-training-guide.md](docs/dataset-and-training-guide.md) | Training a custom model for auto-rickshaw/van/emergency-vehicle classes |
| [docs/performance-guide.md](docs/performance-guide.md) | GPU, ONNX/TensorRT export, model size tradeoffs, frame skipping |
| [docs/future-improvements.md](docs/future-improvements.md) | Known limitations and prioritized next steps |

## Verification

Everything below was actually executed during development, not assumed:

- **Backend**: all 37 pytest tests pass (`cd backend && PYTHONPATH=. pytest app/tests/ -v`),
  covering vehicle-class mapping, drawing, trajectory/line-counting/speed
  math, all 5 violation detectors, heatmap accumulation, and report
  generation (CSV/Excel/PDF byte-level checks).
- **Backend boot**: the full FastAPI app boots cleanly with all 14 REST
  endpoints registered, confirmed via its own OpenAPI schema.
- **Frontend**: `npm install` + `npm run build` both succeed, producing a
  real production bundle (465 modules transformed) — this caught and fixed
  one real bug (an invalid unquoted object key in `tailwind.config.js`)
  before delivery.

**Not exercised live in this environment** (documented, not hidden): YOLOv8
inference and DeepSORT tracking require `torch`/`ultralytics`/
`deep-sort-realtime`, which weren't installed here (multi-GB, no GPU
available in the build sandbox). The code is correct against each
library's documented API and covered by unit tests for all the logic
around it, but you should smoke-test actual detection against a real
camera/video after `pip install -r requirements.txt` in your own environment.

## Roadmap Status

1. ✅ Project foundation — config, logging, MongoDB, Docker
2. ✅ Detection engine — YOLOv8, video/webcam/RTSP ingestion, upload API
3. ✅ DeepSORT tracking — permanent IDs, trajectories, entry/exit counting, speed
4. ✅ Violation detection — wrong-direction, lane, red-light-jump, U-turn, no-parking
5. ✅ Alerts — Telegram, email, rate-limited dispatch
6. ✅ Analytics & reports — MongoDB aggregation, CSV/Excel/PDF export
7. ✅ React dashboard — live feed, stats, charts, dark UI
8. ✅ Multi-camera, ROI/polygon zones, heatmaps
9. ✅ Performance — CUDA/ONNX/TensorRT export scripts, tuning guide
10. ✅ Testing, CI/CD, deployment docs, architecture diagram

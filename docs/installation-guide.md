# Installation Guide

Supports Windows, Linux, and macOS for local development; Linux/Ubuntu is
the tested target for the Docker deployment path.

## Option A: Docker (recommended for a full stack quickly)

**Requirements:** Docker Desktop (Windows/macOS) or Docker Engine + Compose
plugin (Linux).

```bash
git clone <your-repo-url>
cd traffic-ai-system
cp backend/.env.example backend/.env   # edit values as needed
docker compose up --build
```

- Backend: http://localhost:8000/api/docs
- Frontend: http://localhost:5173
- MongoDB: localhost:27017 (internal to the compose network otherwise)

## Option B: Local development (no Docker)

### Backend

**Requirements:** Python 3.11+, MongoDB running locally (or a remote URI).

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
python scripts/download_weights.py --model yolov8n.pt
uvicorn app.main:app --reload
```

MongoDB options:
- Local install: https://www.mongodb.com/docs/manual/installation/
- Docker only for the database: `docker run -d -p 27017:27017 mongo:7.0`
- Managed (MongoDB Atlas free tier): set `MONGO_URI` in `.env` to the
  connection string Atlas gives you.

### Frontend

**Requirements:** Node.js 20+.

```bash
cd frontend
npm install
npm run dev
```

Vite proxies `/api` requests to `http://localhost:8000` in dev (see
`vite.config.js`) — no CORS configuration needed locally.

## GPU support (optional, for faster detection)

By default the app runs on CPU (`DEVICE=cpu` in `.env`). For an NVIDIA GPU:

1. Install CUDA-enabled `torch`/`torchvision` matching your CUDA version
   (see https://pytorch.org/get-started/locally/) instead of the CPU wheels
   `requirements.txt` resolves to by default.
2. Set `DEVICE=cuda` in `.env`.
3. In Docker, install `nvidia-container-toolkit` on the host and uncomment
   the GPU `deploy` block in `docker-compose.yml`.

See `docs/performance-guide.md` for further tuning (ONNX/TensorRT export,
model size tradeoffs, frame skipping).

## Verifying the install

```bash
curl http://localhost:8000/api/health
# {"success": true, "status": "healthy", ...}

cd backend && PYTHONPATH=. pytest app/tests/ -v
# should show 37 passed
```

## Common issues

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError: app` | Run uvicorn from inside `backend/`, not the repo root |
| `pymongo.errors.ServerSelectionTimeoutError` | MongoDB isn't running/reachable; check `MONGO_URI` |
| First detection request hangs ~10-20s | Normal — YOLOv8n weights auto-downloading on first use |
| `RuntimeError: ultralytics is not installed` | `pip install -r requirements.txt` inside the activated venv |
| Frontend shows "Could not reach backend API" | Confirm the backend is running on port 8000 and CORS_ORIGINS in `.env` includes your frontend's origin |
| `Failed to open video source: 0` (webcam) | Wrong device index, or another app has the camera open; try `1`, check `ls /dev/video*` (Linux) |

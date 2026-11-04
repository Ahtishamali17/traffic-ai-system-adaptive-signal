# Deployment Guide

## Overview

Production deployment uses three containers, orchestrated by
`docker-compose.yml`: `mongodb`, `backend` (FastAPI + detection engine),
and `frontend` (React build served by Nginx, which also reverse-proxies
`/api` to the backend). This guide covers a single-host deployment; for
multi-host/Kubernetes, see the notes at the end.

## Prerequisites

- Docker Engine + Compose plugin on the target host (Linux/Ubuntu tested;
  Windows/macOS work for development but aren't the intended production target)
- A domain name and TLS certificate if exposing this publicly (Nginx config
  here serves plain HTTP; put a reverse proxy like Caddy or Nginx+certbot in
  front for TLS, or terminate TLS at a load balancer)
- If using GPU inference: NVIDIA drivers + `nvidia-container-toolkit` on the host

## Step-by-step

### 1. Clone and configure

```bash
git clone <your-repo-url>
cd traffic-ai-system
cp backend/.env.example backend/.env
```

Edit `backend/.env` for production:
```
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate a real random secret>
MONGO_URI=mongodb://mongodb:27017      # matches the compose service name
CORS_ORIGINS=["https://your-domain.com"]
DEVICE=cuda                             # if GPU available, else cpu
```

### 2. Pre-download model weights (avoids a slow first request)

```bash
cd backend
pip install ultralytics --quiet
python scripts/download_weights.py --model yolov8n.pt
cd ..
```

### 3. Build and start

```bash
docker compose up --build -d
```

### 4. Verify

```bash
curl http://localhost:8000/api/health
curl http://localhost:5173/           # frontend served by Nginx
```

### 5. (Optional) GPU inference

Uncomment the `deploy.resources.reservations.devices` block for the
`backend` service in `docker-compose.yml`, ensure
`nvidia-container-toolkit` is installed on the host, then rebuild:

```bash
docker compose up --build -d backend
```

## Production hardening checklist

- [ ] Set a strong, unique `SECRET_KEY` (not the `.env.example` placeholder)
- [ ] Set `DEBUG=False` and `ENVIRONMENT=production`
- [ ] Restrict `CORS_ORIGINS` to your actual frontend domain(s)
- [ ] Put TLS in front (Caddy, Nginx+certbot, or your cloud LB) — this repo's
      Nginx config serves plain HTTP by design, so it can sit behind any of those
- [ ] Set MongoDB authentication (the default `mongo:7.0` image runs without
      auth unless you set `MONGO_INITDB_ROOT_USERNAME`/`PASSWORD` and update
      `MONGO_URI` accordingly) — do this before exposing MongoDB's port publicly,
      or better, don't publish port 27017 externally at all in production
- [ ] Configure Telegram/email alert credentials if you want notifications
- [ ] Set up log rotation monitoring (already configured for 14-day retention
      in `app/core/logging.py`, but confirm disk space is adequate for your
      camera count and retention needs)
- [ ] Set resource limits (`mem_limit`, `cpus`) on the `backend` service in
      `docker-compose.yml` if running alongside other workloads on the host
- [ ] Back up the `mongo_data` volume on a schedule

## Scaling beyond one host

This architecture's one deliberate constraint: `SessionManager` and
`AlertService`'s rate-limit state are process-local (in-memory), not shared
across multiple backend replicas. Running more than one `backend` container
behind a load balancer will cause each replica to track its own detection
sessions independently — a session started on replica A won't be visible
from replica B.

To scale beyond a single backend process:
- Move session/alert state to Redis (swap the in-memory dicts in
  `SessionManager`/`AlertService` for Redis-backed equivalents)
- Or, pin each camera to a specific backend replica via a session-affinity
  load balancer rule (simpler, sufficient for most deployments — traffic
  cameras are typically fixed to a specific processing node anyway)

MongoDB itself scales normally (replica sets, sharding) with no
application-level changes needed, since all writes already go through a
single `MONGO_URI`.

## Rolling back

```bash
docker compose down
git checkout <previous-tag>
docker compose up --build -d
```

MongoDB data persists in the `mongo_data` named volume independent of
container rebuilds, so rolling back the application code doesn't affect
stored events/violations.

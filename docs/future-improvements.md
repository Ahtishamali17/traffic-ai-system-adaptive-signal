# Future Improvements

Honest accounting of what this system does well, what's simplified for a
buildable scope, and what a next iteration should prioritize.

## Known limitations (by design, documented rather than hidden)

- **Speed estimation accuracy** depends entirely on `pixels_per_meter`
  calibration, set manually per camera. It's a reasonable approximation,
  not radar-grade — don't use it for legal enforcement without a proper
  calibration procedure and validation against a known-speed reference.
- **Auto-rickshaw, van, and emergency-vehicle detection** require a
  custom-trained model (see `docs/dataset-and-training-guide.md`) — stock
  YOLOv8/COCO weights don't recognize these classes out of the box.
- **Red-light-jump detection uses a simulated signal cycle**
  (`SignalCycleSimulator`), not a real traffic-signal controller feed, per
  the original spec's "simulate" requirement. Real deployments need to feed
  actual signal state in via `ViolationEngine.signal_simulator` or a new
  external-feed integration.
- **Session/alert state is process-local**, not distributed — see the
  "Scaling beyond one host" section in `docs/deployment-guide.md`.
- **The "suspicious vehicle" alert is a crude loitering heuristic**
  (track present >120s without leaving) — it's a placeholder for a real
  behavior-anomaly model, not a claim of actual suspicious-behavior detection.
- **No authentication/authorization layer yet** — every API endpoint is
  currently open. Fine for a local/trusted-network deployment; not fine for
  a public-internet deployment without adding an auth layer first.

## High-value next steps

1. **Authentication & multi-tenancy** — API keys or OAuth for the REST API,
   per-user camera access control, audit logging of who started/stopped
   sessions and downloaded reports.
2. **Real signal-controller integration** — replace `SignalCycleSimulator`
   with a real feed (many traffic controllers expose NTCIP or a simple
   digital I/O signal you could poll/subscribe to).
3. **Distributed session state** — Redis-backed `SessionManager` and
   `AlertService` to support horizontal scaling across multiple backend
   replicas.
4. **Batch/offline video analysis endpoint** — process an uploaded video
   faster than real-time using batched YOLO inference (see the "Batch
   processing" section of `docs/performance-guide.md`), useful for
   after-the-fact review of long recordings rather than only live streams.
5. **Custom vehicle-class model** — train on a real, region-specific
   dataset for auto-rickshaw/van/emergency-vehicle detection, following
   `docs/dataset-and-training-guide.md`.
6. **Automatic camera calibration** — infer `pixels_per_meter` from a
   known reference object (e.g. standard lane width) instead of requiring
   manual measurement per camera.
7. **Historical violation review UI** — the backend already persists every
   violation to MongoDB with a bounding box and timestamp; the frontend
   doesn't yet have a searchable/filterable violation log page (only the
   live "last 50" list on the Live Detection page).
8. **WebSocket-based live stats** instead of the frontend's current 2-10
   second polling — lower latency for FPS/count updates, less request overhead.
9. **Multi-camera correlation** — track a vehicle across multiple camera
   views (e.g. entering at gate-1, exiting at gate-2) using re-identification,
   not just per-camera tracking.
10. **Automated model retraining pipeline** — feed confirmed violations/
    corrections back into a labeled dataset for periodic fine-tuning,
    closing the loop between deployment and model quality.

## Explicitly out of scope for this build

- Kubernetes manifests (Docker Compose covers the single-host case this
  build targets; a K8s port is straightforward but a distinct deliverable)
- Mobile native apps (the React dashboard is responsive but not a
  dedicated iOS/Android app)
- On-device/edge inference (Jetson, Coral, etc.) — the architecture would
  need a lighter-weight inference runtime swap, documented as a possible
  direction but not implemented here

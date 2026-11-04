# Performance Optimization Guide

This system is CPU-runnable out of the box (`DEVICE=cpu`, `yolov8n.pt`),
but for production traffic volumes you'll want to tune the knobs below.
Ordered roughly by impact-per-effort.

## 1. GPU acceleration (CUDA)

The single biggest lever. Set in `backend/.env`:

```
DEVICE=cuda
```

Requirements: an NVIDIA GPU, CUDA drivers installed on the host, and
`torch`/`torchvision` installed with CUDA support (the versions pinned in
`requirements.txt` are CPU-compatible; for GPU, install the matching
`+cu121`-style wheel from https://pytorch.org/get-started/locally/ instead).

In Docker, uncomment the `deploy.resources.reservations.devices` block for
the `backend` service in `docker-compose.yml` and install the
`nvidia-container-toolkit` on the host.

## 2. Smaller/larger model checkpoint

`MODEL_WEIGHTS_PATH` controls speed/accuracy tradeoff:

| Checkpoint   | Relative speed | Relative accuracy |
|--------------|-----------------|--------------------|
| yolov8n.pt   | fastest         | lowest             |
| yolov8s.pt   | fast            | low-medium         |
| yolov8m.pt   | medium          | medium-high        |
| yolov8l.pt   | slow            | high               |
| yolov8x.pt   | slowest         | highest            |

Start with `yolov8n.pt` on CPU, `yolov8s.pt`/`yolov8m.pt` on GPU.

## 3. ONNX / TensorRT export

`scripts/export_model.py` converts a `.pt` checkpoint to a faster runtime
format:

```bash
# Portable, CPU or GPU, ~1.3-2x faster than raw PyTorch
python scripts/export_model.py --weights models/weights/yolov8n.pt --format onnx

# NVIDIA GPU only, fastest available, but hardware/TensorRT-version specific
python scripts/export_model.py --weights models/weights/yolov8n.pt --format engine --half
```

Point `MODEL_WEIGHTS_PATH` at the exported file afterward. `VehicleDetector`
loads `.onnx`/`.engine` files exactly like `.pt` -- no code changes needed.

**Note on TensorRT engines:** they are compiled for the exact GPU model and
TensorRT/CUDA version that built them. Rebuild the `.engine` file on (or for)
each deployment target rather than committing it to source control.

## 4. Mixed precision (FP16)

`--half` in the export script above, or on GPU inference directly by passing
`half=True` through to Ultralytics -- roughly halves memory usage and
speeds up inference on GPUs with Tensor Cores, at a small, usually
imperceptible, accuracy cost. Not supported on CPU.

## 5. Frame skipping

`frame_skip` in the `POST /detection/start` request processes every Nth
frame instead of every frame -- the cheapest lever with zero code changes.
`frame_skip=2` roughly halves detection load with a small hit to tracking
smoothness and speed-estimation precision (fewer trajectory samples).

## 6. Multithreading (already built in)

Every detection session already runs in its own background thread
(`app/services/detection_session.py`), so multiple cameras process in
parallel rather than serially. This is inherent to the architecture, not a
toggle -- no action needed, but it's why CPU core count matters for
multi-camera deployments more than single-camera FPS does.

## 7. Batch processing

For **offline** processing of many recorded videos (not live streams),
batch multiple frames into a single `model.predict()` call rather than
one-frame-at-a-time -- Ultralytics accepts a list of frames/images and
processes them as one batched forward pass, which is meaningfully faster
per-frame on GPU. This isn't wired into the live-session pipeline (live
detection is inherently one-frame-at-a-time as frames arrive), but is worth
adding as a separate "batch analyze this video" endpoint if bulk offline
processing becomes a requirement.

## Quick reference: what to change for common goals

| Goal                              | Change |
|------------------------------------|--------|
| Cheapest way to get more FPS       | Increase `frame_skip` |
| Best accuracy/speed balance on CPU | `yolov8n.pt` + ONNX export |
| Best accuracy/speed balance on GPU | `yolov8s.pt`/`yolov8m.pt` + CUDA + FP16 |
| Absolute max throughput on GPU     | TensorRT `.engine` + FP16 + CUDA |
| Many cameras, modest hardware      | Smaller model + higher `frame_skip` per camera |

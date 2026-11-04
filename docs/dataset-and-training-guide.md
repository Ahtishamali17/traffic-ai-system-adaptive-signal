# Dataset & Training Guide

## Why you might need to train a custom model

Stock YOLOv8 weights (`yolov8n.pt` etc.) are trained on COCO, which covers
5 of this system's 8 target vehicle classes: `car`, `truck`, `bus`,
`motorcycle`, `bicycle`. It has **no concept** of `auto_rickshaw`, `van`
(COCO's "car"/"truck" don't distinguish it), or `emergency_vehicle`. To
detect those, you need a custom-trained or fine-tuned model. This guide
covers both fine-tuning stock weights and training from a public dataset.

## Recommended datasets

| Dataset | Good for | Notes |
|---------|----------|-------|
| [COCO](https://cocodataset.org) | General object detection baseline | Already baked into stock YOLOv8 weights |
| [BDD100K](https://bdd-data.berkeley.edu/) | Diverse driving conditions (weather, time of day) | Large (100k images), strong for dashcam/CCTV-style footage |
| [UA-DETRAC](https://detrac-db.rit.albany.edu/) | Dense traffic, vehicle tracking benchmarks | Good complement to BDD100K for occlusion-heavy scenes |
| Custom dataset | Auto-rickshaw, emergency vehicles, region-specific vehicle types | Required for classes not in the above |

## Building a custom dataset

1. **Collect footage** representative of your actual deployment cameras
   (angle, resolution, lighting) — a model trained on downtown daylight
   traffic will underperform on a rural nighttime camera.
2. **Extract frames** at a reasonable interval (e.g. 1 frame/second) to
   avoid near-duplicate images dominating the dataset.
3. **Annotate** bounding boxes with a tool like
   [Roboflow](https://roboflow.com), [CVAT](https://cvat.ai), or
   [LabelImg](https://github.com/heartexlabs/labelImg), exporting in
   YOLO format (one `.txt` per image: `class_id x_center y_center width height`,
   normalized 0–1).
4. **Split** into train/val/test (typical: 70/20/10).
5. **Write a `data.yaml`**:

```yaml
path: /path/to/dataset
train: images/train
val: images/val
test: images/test

names:
  0: car
  1: truck
  2: bus
  3: motorcycle
  4: bicycle
  5: auto_rickshaw
  6: van
  7: emergency_vehicle
```

Important: if you fine-tune from stock COCO weights, your class indices
here don't need to match COCO's — Ultralytics replaces the detection head
for the new class count during fine-tuning.

## Training

```bash
pip install ultralytics  # already in requirements.txt

yolo detect train \
  data=/path/to/data.yaml \
  model=yolov8n.pt \
  epochs=100 \
  imgsz=640 \
  batch=16 \
  device=0 \
  project=runs/traffic \
  name=custom_v1
```

Or via Python (equivalent, useful if you want to script sweeps):

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")  # start from stock weights (transfer learning)
model.train(data="data.yaml", epochs=100, imgsz=640, batch=16, device=0)
```

Key parameters:
- `epochs`: 100 is a reasonable starting point; watch validation mAP for
  plateauing and use early stopping (`patience=20`) to avoid overfitting.
- `imgsz`: match your camera's typical resolution/aspect ratio if possible;
  640 is the YOLOv8 default and a good balance of speed/accuracy.
- `batch`: as large as your GPU memory allows; reduce if you hit OOM errors.

## Evaluating

```bash
yolo detect val model=runs/traffic/custom_v1/weights/best.pt data=/path/to/data.yaml
```

Look at per-class mAP@0.5 — if `auto_rickshaw` or `emergency_vehicle` (your
custom classes) score much lower than `car`/`truck`, you likely need more
training examples for those specific classes, not more epochs.

## Deploying the trained model

```bash
cp runs/traffic/custom_v1/weights/best.pt backend/models/weights/traffic_custom.pt
```

Then in `backend/.env`:

```
MODEL_WEIGHTS_PATH=models/weights/traffic_custom.pt
```

**Also update `app/core/vehicle_classes.py`** — if your custom model's
class ordering differs from the built-in `COCO_ID_TO_VEHICLE_NAME` mapping,
update it to match your `data.yaml`'s class indices, or detection results
will be labeled incorrectly even though the boxes are accurate.

Finally, consider exporting to ONNX/TensorRT for faster inference — see
`docs/performance-guide.md` and `scripts/export_model.py`.

"""
app/core/vehicle_classes.py
--------------------------------------------------------------------
Central definition of every vehicle class the system understands,
mapped to:
  - the COCO class id/name YOLOv8's pretrained weights output
  - a display color (BGR, for OpenCV drawing)
  - a human-readable label shown in the UI

Why this matters: YOLOv8's stock COCO weights (yolov8n/s/m/l/x.pt)
only recognize 5 of our target classes out of the box: bicycle, car,
motorcycle, bus, truck. Classes like "auto_rickshaw", "van", and
"emergency_vehicle" are NOT in COCO and require a custom-trained or
fine-tuned model (covered in docs/training-guide.md, added in a
later step). This module keeps that mapping explicit and in one
place so the rest of the code never hardcodes class IDs.
--------------------------------------------------------------------
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class VehicleClassInfo:
    coco_id: int | None   # None if not detectable by stock COCO weights
    label: str             # human-readable label shown in the UI
    color_bgr: tuple[int, int, int]  # OpenCV uses BGR, not RGB


# COCO ids for reference: 1=bicycle, 2=car, 3=motorcycle, 5=bus, 7=truck
VEHICLE_CLASSES: dict[str, VehicleClassInfo] = {
    "bicycle":          VehicleClassInfo(1, "Bicycle",          (0, 200, 255)),   # amber
    "car":              VehicleClassInfo(2, "Car",              (0, 255, 0)),     # green
    "motorcycle":       VehicleClassInfo(3, "Motorcycle",       (255, 0, 255)),   # magenta
    "bus":              VehicleClassInfo(5, "Bus",              (255, 128, 0)),   # blue-orange
    "truck":            VehicleClassInfo(7, "Truck",            (0, 128, 255)),   # orange
    # Not present in stock COCO weights -- require a custom-trained model.
    # Kept here so the rest of the pipeline (schemas, DB, analytics, UI)
    # already understands these labels once a fine-tuned model is swapped in.
    "auto_rickshaw":    VehicleClassInfo(None, "Auto Rickshaw",  (255, 255, 0)),
    "van":              VehicleClassInfo(None, "Van",            (180, 105, 255)),
    "emergency_vehicle": VehicleClassInfo(None, "Emergency Vehicle", (0, 0, 255)),
}

# Reverse lookup: COCO class id -> our internal vehicle class name.
# Only includes classes actually detectable by stock COCO weights.
COCO_ID_TO_VEHICLE_NAME: dict[int, str] = {
    info.coco_id: name
    for name, info in VEHICLE_CLASSES.items()
    if info.coco_id is not None
}


def is_stock_detectable(vehicle_name: str) -> bool:
    """True if this class can be detected by stock COCO-pretrained YOLOv8 weights."""
    info = VEHICLE_CLASSES.get(vehicle_name)
    return info is not None and info.coco_id is not None


def get_color(vehicle_name: str) -> tuple[int, int, int]:
    """Return the BGR draw color for a vehicle class, defaulting to white."""
    info = VEHICLE_CLASSES.get(vehicle_name)
    return info.color_bgr if info else (255, 255, 255)

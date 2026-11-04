"""
Unit tests for app/core/vehicle_classes.py and app/utils/draw.py.
These deliberately avoid loading YOLO/torch so they run fast in CI
without a GPU or large model download.
"""

import numpy as np

from app.core.vehicle_classes import (
    COCO_ID_TO_VEHICLE_NAME,
    VEHICLE_CLASSES,
    get_color,
    is_stock_detectable,
)
from app.schemas.detection import BoundingBox, VehicleDetection
from app.utils.draw import draw_detections, draw_stats_overlay, encode_jpeg


def test_all_eight_target_classes_defined():
    expected = {
        "car", "truck", "bus", "motorcycle", "auto_rickshaw",
        "van", "bicycle", "emergency_vehicle",
    }
    assert expected == set(VEHICLE_CLASSES.keys())


def test_stock_detectable_classes():
    assert is_stock_detectable("car")
    assert is_stock_detectable("bicycle")
    assert not is_stock_detectable("auto_rickshaw")
    assert not is_stock_detectable("emergency_vehicle")


def test_coco_id_mapping_has_no_collisions():
    # 5 stock-detectable classes -> 5 distinct COCO ids
    assert len(COCO_ID_TO_VEHICLE_NAME) == 5
    assert COCO_ID_TO_VEHICLE_NAME[2] == "car"
    assert COCO_ID_TO_VEHICLE_NAME[7] == "truck"


def test_get_color_returns_default_for_unknown_class():
    assert get_color("unicorn") == (255, 255, 255)


def test_draw_detections_does_not_crash_and_returns_same_shape():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = [
        VehicleDetection(
            class_name="car", confidence=0.87,
            bbox=BoundingBox(x1=50, y1=50, x2=200, y2=150), track_id=1,
        ),
        VehicleDetection(
            class_name="truck", confidence=0.65,
            bbox=BoundingBox(x1=300, y1=200, x2=450, y2=350), track_id=None,
        ),
    ]
    annotated = draw_detections(frame.copy(), detections)
    assert annotated.shape == frame.shape


def test_draw_stats_overlay_does_not_crash():
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    annotated = draw_stats_overlay(
        frame.copy(), fps=24.3, vehicle_count=5, inference_ms=18.2, camera_id="gate-1",
    )
    assert annotated.shape == frame.shape


def test_encode_jpeg_produces_nonempty_bytes():
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    data = encode_jpeg(frame)
    assert isinstance(data, bytes)
    assert len(data) > 0
    # JPEG magic number
    assert data[:2] == b"\xff\xd8"

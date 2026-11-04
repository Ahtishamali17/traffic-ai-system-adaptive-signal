"""
app/services/detector.py
--------------------------------------------------------------------
Thin, production-friendly wrapper around Ultralytics YOLOv8.

Responsibilities:
  - Load the model once (expensive) and reuse it across every frame
    and every session (the model is NOT re-loaded per request).
  - Run inference on a single BGR frame (numpy array from OpenCV).
  - Filter raw YOLO output down to the vehicle classes we care about.
  - Return plain-Python detection objects, decoupled from Ultralytics'
    internal Results object so the rest of the app never imports
    ultralytics directly.

This class is intentionally NOT a singleton at import time -- it's
instantiated once by `get_detector()` (cached) so tests can swap in
a mock without touching global state.
--------------------------------------------------------------------
"""

from __future__ import annotations

import time
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.core.config import get_settings
from app.core.logging import logger
from app.core.vehicle_classes import COCO_ID_TO_VEHICLE_NAME
from app.schemas.detection import BoundingBox, VehicleDetection

settings = get_settings()


class ModelLoadError(RuntimeError):
    """Raised when the YOLO weights file is missing or fails to load."""


class VehicleDetector:
    """Wraps a YOLOv8 model, restricted to vehicle classes, ready for inference."""

    def __init__(
        self,
        weights_path: str | None = None,
        device: str | None = None,
        confidence_threshold: float | None = None,
        iou_threshold: float | None = None,
    ) -> None:
        self.weights_path = weights_path or settings.MODEL_WEIGHTS_PATH
        self.device = device or settings.DEVICE
        self.confidence_threshold = confidence_threshold or settings.CONFIDENCE_THRESHOLD
        self.iou_threshold = iou_threshold or settings.IOU_THRESHOLD
        self._model = None
        self._load_model()

    def _load_model(self) -> None:
        """
        Load YOLOv8 weights. Ultralytics will auto-download stock COCO
        weights (e.g. 'yolov8n.pt') on first use if the exact filename
        matches a known pretrained model and the file doesn't exist yet
        locally. Custom-trained weights (best.pt from Step 9's training
        guide) must already exist at `weights_path`.
        """
        try:
            from ultralytics import YOLO  # imported lazily: heavy dependency
        except ImportError as exc:
            raise ModelLoadError(
                "ultralytics is not installed. Run: pip install -r requirements.txt"
            ) from exc

        weights_file = Path(self.weights_path)
        is_stock_name = weights_file.name in {
            "yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"
        }

        if not weights_file.exists() and not is_stock_name:
            raise ModelLoadError(
                f"Model weights not found at '{self.weights_path}' and it is not "
                f"a recognized stock YOLOv8 checkpoint name. Either place your "
                f"custom-trained weights there, or set MODEL_WEIGHTS_PATH to a "
                f"stock name like 'yolov8n.pt' to auto-download."
            )

        logger.info(f"Loading YOLOv8 model: {self.weights_path} on device={self.device}")
        t0 = time.perf_counter()
        try:
            self._model = YOLO(str(weights_file) if weights_file.exists() else self.weights_path)
            self._model.to(self.device)
        except Exception as exc:
            raise ModelLoadError(f"Failed to load YOLOv8 weights: {exc}") from exc

        logger.info(f"Model loaded in {time.perf_counter() - t0:.2f}s")

    def detect(self, frame: np.ndarray) -> tuple[list[VehicleDetection], float]:
        """
        Run inference on a single frame.

        Args:
            frame: BGR image as a numpy array (as returned by cv2.VideoCapture.read())

        Returns:
            (detections, inference_ms)
        """
        if self._model is None:
            raise ModelLoadError("Model is not loaded")

        t0 = time.perf_counter()
        results = self._model.predict(
            source=frame,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            device=self.device,
            verbose=False,
        )
        inference_ms = (time.perf_counter() - t0) * 1000

        detections: list[VehicleDetection] = []
        if not results:
            return detections, inference_ms

        result = results[0]
        boxes = result.boxes
        if boxes is None:
            return detections, inference_ms

        for box in boxes:
            cls_id = int(box.cls[0])
            vehicle_name = COCO_ID_TO_VEHICLE_NAME.get(cls_id)
            if vehicle_name is None:
                continue  # not one of our target vehicle classes (e.g. "person", "dog")

            conf = float(box.conf[0])
            x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())

            detections.append(
                VehicleDetection(
                    class_name=vehicle_name,
                    confidence=round(conf, 4),
                    bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    track_id=None,  # DeepSORT assigns this in Step 3
                )
            )

        return detections, inference_ms


@lru_cache
def get_detector() -> VehicleDetector:
    """
    FastAPI dependency: returns a single shared VehicleDetector instance.
    Cached so the (expensive) model load happens exactly once per process.
    """
    return VehicleDetector()

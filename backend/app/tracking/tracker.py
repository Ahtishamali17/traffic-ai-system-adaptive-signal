"""
app/tracking/tracker.py
--------------------------------------------------------------------
Wraps `deep_sort_realtime` to turn per-frame YOLOv8 detections (which
have no memory of previous frames) into tracked vehicles with a
permanent ID that persists across frames, occlusions, and brief
detection dropouts.

Kept separate from VehicleDetector: detection (what/where in THIS
frame) and tracking (which one is the SAME vehicle across frames)
are different concerns with different failure modes and different
tunable parameters (max_age, n_init, IOU vs. appearance matching).
--------------------------------------------------------------------
"""

from __future__ import annotations

import numpy as np

from app.core.logging import logger
from app.schemas.detection import BoundingBox, VehicleDetection


class VehicleTracker:
    """Assigns and maintains permanent track IDs across frames via DeepSORT."""

    def __init__(self, max_age: int = 30, n_init: int = 3, max_iou_distance: float = 0.7):
        """
        Args:
            max_age: frames a track survives with no matching detection
                     before being deleted (handles brief occlusion).
            n_init:  consecutive detections required before a track is
                     "confirmed" (filters out one-frame false positives).
            max_iou_distance: max IOU distance for the fallback matching
                     cascade stage.
        """
        try:
            from deep_sort_realtime.deepsort_tracker import DeepSort
        except ImportError as exc:
            raise RuntimeError(
                "deep-sort-realtime is not installed. Run: pip install -r requirements.txt"
            ) from exc

        self._tracker = DeepSort(
            max_age=max_age,
            n_init=n_init,
            max_iou_distance=max_iou_distance,
            embedder="mobilenet",     # lightweight appearance embedder, CPU-friendly
            half=False,
            bgr=True,                 # OpenCV frames are BGR
        )
        logger.info(f"VehicleTracker initialized (max_age={max_age}, n_init={n_init})")

    def update(self, detections: list[VehicleDetection], frame: np.ndarray) -> list[VehicleDetection]:
        """
        Feed one frame's raw detections through DeepSORT and return the
        same vehicles annotated with a permanent `track_id`.

        Detections that DeepSORT hasn't confirmed yet (fewer than n_init
        consecutive matches) are dropped from the output -- this is what
        filters out flickering one-frame false positives.
        """
        if not detections:
            # Still call update_tracks with an empty list so internal track
            # ages advance correctly (otherwise tracks appear artificially
            # long-lived across frames with zero detections).
            self._tracker.update_tracks([], frame=frame)
            return []

        raw_detections = [
            (
                [d.bbox.x1, d.bbox.y1, d.bbox.x2 - d.bbox.x1, d.bbox.y2 - d.bbox.y1],  # ltwh
                d.confidence,
                d.class_name,
            )
            for d in detections
        ]

        tracks = self._tracker.update_tracks(raw_detections, frame=frame)

        tracked: list[VehicleDetection] = []
        for track in tracks:
            if not track.is_confirmed():
                continue

            ltrb = track.to_ltrb()  # [left, top, right, bottom]
            x1, y1, x2, y2 = (int(v) for v in ltrb)
            class_name = track.get_det_class() or "car"  # fallback if class metadata is missing
            confidence = track.get_det_conf()
            confidence = float(confidence) if confidence is not None else 0.0

            tracked.append(
                VehicleDetection(
                    class_name=class_name,
                    confidence=round(confidence, 4),
                    bbox=BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2),
                    track_id=int(track.track_id),
                )
            )

        return tracked


def get_centroid(bbox: BoundingBox) -> tuple[float, float]:
    """Center point of a bounding box, used for trajectory/line-crossing math."""
    return ((bbox.x1 + bbox.x2) / 2, (bbox.y1 + bbox.y2) / 2)

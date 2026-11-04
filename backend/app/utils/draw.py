"""
app/utils/draw.py
--------------------------------------------------------------------
OpenCV drawing helpers for annotating frames with detection results.
Kept separate from the detector so the AI logic has zero rendering
concerns, and separate from the API layer so it's independently
unit-testable.
--------------------------------------------------------------------
"""

from __future__ import annotations

import cv2
import numpy as np

from app.core.vehicle_classes import get_color
from app.schemas.detection import CountingLineConfig, VehicleDetection
from app.schemas.signal import IntersectionStatus, LaneZone, SignalPhase
from app.schemas.tracking import TrackPoint

FONT = cv2.FONT_HERSHEY_SIMPLEX


def draw_detections(
    frame: np.ndarray,
    detections: list[VehicleDetection],
    speeds_kmph: dict[int, float] | None = None,
    overspeed_ids: set[int] | None = None,
) -> np.ndarray:
    """
    Draws a bounding box + label ("ClassName ID:xx 92% 34km/h") for every
    detection. Mutates and returns the same frame (caller decides
    whether to copy first). Overspeeding tracks are drawn in red
    regardless of their vehicle-class color, as a visual alert.
    """
    speeds_kmph = speeds_kmph or {}
    overspeed_ids = overspeed_ids or set()

    for det in detections:
        is_overspeed = det.track_id in overspeed_ids
        color = (0, 0, 255) if is_overspeed else get_color(det.class_name)
        x1, y1, x2, y2 = det.bbox.x1, det.bbox.y1, det.bbox.x2, det.bbox.y2

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, lineType=cv2.LINE_AA)

        id_part = f" ID:{det.track_id}" if det.track_id is not None else ""
        speed_part = ""
        if det.track_id is not None and det.track_id in speeds_kmph:
            speed_part = f" {speeds_kmph[det.track_id]:.0f}km/h"
        label = (
            f"{det.class_name.replace('_', ' ').title()}{id_part} "
            f"{det.confidence * 100:.0f}%{speed_part}"
        )

        (text_w, text_h), baseline = cv2.getTextSize(label, FONT, 0.5, 1)
        label_y1 = max(y1 - text_h - baseline - 4, 0)
        cv2.rectangle(frame, (x1, label_y1), (x1 + text_w + 4, y1), color, -1)
        cv2.putText(
            frame, label, (x1 + 2, y1 - baseline - 2),
            FONT, 0.5, (0, 0, 0), 1, lineType=cv2.LINE_AA,
        )

    return frame


def draw_trail(frame: np.ndarray, points: list[TrackPoint], color: tuple[int, int, int]) -> np.ndarray:
    """Draws a fading trail line through a track's recent centroid history."""
    if len(points) < 2:
        return frame

    pts = [(int(p.x), int(p.y)) for p in points]
    n = len(pts)
    for i in range(1, n):
        # Older segments are thinner/dimmer to convey motion direction visually.
        thickness = max(1, int(3 * (i / n)))
        cv2.line(frame, pts[i - 1], pts[i], color, thickness, lineType=cv2.LINE_AA)

    return frame


def draw_counting_line(frame: np.ndarray, line: CountingLineConfig) -> np.ndarray:
    """Draws the configured virtual entry/exit line with labels at each end."""
    a, b = (line.point_a.x, line.point_a.y), (line.point_b.x, line.point_b.y)
    cv2.line(frame, a, b, (0, 255, 255), 2, lineType=cv2.LINE_AA)
    cv2.circle(frame, a, 5, (0, 255, 255), -1)
    cv2.circle(frame, b, 5, (0, 255, 255), -1)
    cv2.putText(frame, line.entry_label, (a[0] + 8, a[1] - 8), FONT, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
    cv2.putText(frame, line.exit_label, (b[0] + 8, b[1] - 8), FONT, 0.5, (0, 255, 255), 1, cv2.LINE_AA)
    return frame


_SIGNAL_PHASE_COLOR = {
    SignalPhase.GREEN: (0, 200, 0),
    SignalPhase.YELLOW: (0, 200, 255),
    SignalPhase.RED: (0, 0, 220),
}


def draw_lane_zones(frame: np.ndarray, lanes: list[LaneZone], status: IntersectionStatus) -> np.ndarray:
    """
    Draws each lane's polygon outlined in its current signal color (green/
    yellow/red), with the lane name, live density, and remaining seconds
    for the active lane -- the visual companion to the adaptive signal
    controller's decisions.
    """
    status_by_name = {lane_status.lane_name: lane_status for lane_status in status.lanes}

    for lane in lanes:
        lane_status = status_by_name.get(lane.name)
        if lane_status is None:
            continue

        color = _SIGNAL_PHASE_COLOR[lane_status.phase]
        pts = np.array([[p.x, p.y] for p in lane.polygon], dtype=np.int32)

        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], color)
        cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
        cv2.polylines(frame, [pts], isClosed=True, color=color, thickness=2, lineType=cv2.LINE_AA)

        label_pos = (int(pts[:, 0].mean()) - 40, int(pts[:, 1].mean()))
        label = f"{lane.name}: {lane_status.phase.value.upper()}"
        if lane_status.phase == SignalPhase.GREEN:
            label += f" ({lane_status.remaining_seconds:.0f}s)"
        cv2.putText(frame, label, label_pos, FONT, 0.5, color, 2, cv2.LINE_AA)
        cv2.putText(
            frame, f"density: {lane_status.current_density:.1f}",
            (label_pos[0], label_pos[1] + 18), FONT, 0.45, (200, 200, 200), 1, cv2.LINE_AA,
        )

    return frame


def draw_stats_overlay(
    frame: np.ndarray,
    *,
    fps: float,
    vehicle_count: int,
    inference_ms: float,
    camera_id: str,
    entry_count: int | None = None,
    exit_count: int | None = None,
) -> np.ndarray:
    """Draws a small semi-transparent stats panel in the top-left corner."""
    overlay = frame.copy()
    panel_h = 100 if entry_count is None else 120
    panel_w = 230
    cv2.rectangle(overlay, (0, 0), (panel_w, panel_h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    lines = [
        f"Camera: {camera_id}",
        f"FPS: {fps:.1f}",
        f"Vehicles: {vehicle_count}",
        f"Inference: {inference_ms:.1f} ms",
    ]
    if entry_count is not None and exit_count is not None:
        lines.append(f"IN: {entry_count}  OUT: {exit_count}")

    for i, line in enumerate(lines):
        cv2.putText(
            frame, line, (10, 22 + i * 20),
            FONT, 0.5, (0, 255, 180), 1, lineType=cv2.LINE_AA,
        )

    return frame


def encode_jpeg(frame: np.ndarray, quality: int = 80) -> bytes:
    """Encode a frame as JPEG bytes for MJPEG streaming."""
    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("Failed to encode frame as JPEG")
    return buffer.tobytes()

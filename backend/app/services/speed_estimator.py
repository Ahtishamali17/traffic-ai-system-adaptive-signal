"""
app/services/speed_estimator.py
--------------------------------------------------------------------
Estimates vehicle speed from consecutive positions in its trajectory
history. This is a classic frame-difference / pixel-displacement
approach:

    speed = (pixel_distance / pixels_per_meter) / time_delta_seconds

`pixels_per_meter` is a camera-specific calibration constant (set
via a known real-world reference, e.g. lane width or a marked
distance in the camera's field of view) -- configurable per camera
in Settings. This gives an approximation, not radar-grade accuracy;
that limitation is documented for the user rather than hidden.
--------------------------------------------------------------------
"""

from __future__ import annotations

from collections import defaultdict

from app.core.logging import logger
from app.tracking.trajectory import TrackHistory

KMPH_PER_MPS = 3.6


class SpeedEstimator:
    """Computes instantaneous and rolling-average speed per track."""

    def __init__(self, pixels_per_meter: float, speed_limit_kmph: float, smoothing_window: int = 5):
        if pixels_per_meter <= 0:
            raise ValueError("pixels_per_meter must be positive")
        self.pixels_per_meter = pixels_per_meter
        self.speed_limit_kmph = speed_limit_kmph
        self.smoothing_window = smoothing_window
        self._speed_history: dict[int, list[float]] = defaultdict(list)

    def estimate(self, history: TrackHistory) -> tuple[float | None, float | None, bool]:
        """
        Returns (instantaneous_speed_kmph, average_speed_kmph, is_overspeed).
        Returns (None, None, False) if there isn't enough trajectory data yet.
        """
        if len(history.points) < 2:
            return None, None, False

        p_prev, p_curr = history.points[-2], history.points[-1]
        dt = p_curr.timestamp - p_prev.timestamp
        if dt <= 0:
            return None, None, False

        pixel_dist = ((p_curr.x - p_prev.x) ** 2 + (p_curr.y - p_prev.y) ** 2) ** 0.5
        meters = pixel_dist / self.pixels_per_meter
        speed_mps = meters / dt
        speed_kmph = speed_mps * KMPH_PER_MPS

        history_list = self._speed_history[history.track_id]
        history_list.append(speed_kmph)
        if len(history_list) > self.smoothing_window:
            history_list.pop(0)

        avg_speed_kmph = sum(history_list) / len(history_list)
        is_overspeed = avg_speed_kmph > self.speed_limit_kmph

        if is_overspeed:
            logger.debug(
                f"Track {history.track_id} overspeed: {avg_speed_kmph:.1f} km/h "
                f"(limit {self.speed_limit_kmph} km/h)"
            )

        return round(speed_kmph, 1), round(avg_speed_kmph, 1), is_overspeed

    def remove_track(self, track_id: int) -> None:
        self._speed_history.pop(track_id, None)

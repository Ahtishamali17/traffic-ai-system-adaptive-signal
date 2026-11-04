"""
app/tracking/trajectory.py
--------------------------------------------------------------------
Keeps a bounded history of centroid positions for every active
track ID, so we can compute speed, direction, and draw a "trail"
behind each vehicle. This is pure Python/collections state -- no
CV or ML dependency -- so it's cheap to unit test in isolation.
--------------------------------------------------------------------
"""

from __future__ import annotations

import math
import time
from collections import deque
from dataclasses import dataclass, field

from app.schemas.tracking import TrackPoint

# How many recent points to retain per track (limits memory for long-lived
# tracks and bounds the trail-drawing cost).
MAX_TRAJECTORY_POINTS = 50


@dataclass
class TrackHistory:
    track_id: int
    class_name: str
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    points: deque[TrackPoint] = field(default_factory=lambda: deque(maxlen=MAX_TRAJECTORY_POINTS))
    frames_seen: int = 0

    def add_point(self, x: float, y: float, timestamp: float | None = None) -> None:
        ts = timestamp if timestamp is not None else time.time()
        self.points.append(TrackPoint(x=x, y=y, timestamp=ts))
        self.last_seen = ts
        self.frames_seen += 1

    @property
    def lifetime_seconds(self) -> float:
        return max(0.0, self.last_seen - self.first_seen)

    def direction(self) -> str:
        """
        Rough cardinal direction of recent motion, derived from the vector
        between the oldest and newest retained points. Good enough for a
        UI label; wrong-direction violation logic (Step 4) does its own
        more precise check against a configured "correct" direction.
        """
        if len(self.points) < 2:
            return "stationary"

        p_old, p_new = self.points[0], self.points[-1]
        dx, dy = p_new.x - p_old.x, p_new.y - p_old.y

        if abs(dx) < 5 and abs(dy) < 5:
            return "stationary"

        angle = math.degrees(math.atan2(dy, dx))  # image coords: y grows downward
        if -45 <= angle < 45:
            return "right"
        elif 45 <= angle < 135:
            return "down"
        elif -135 <= angle < -45:
            return "up"
        else:
            return "left"


class TrajectoryStore:
    """Registry of TrackHistory objects for every track_id seen this session."""

    def __init__(self, max_age_seconds: float = 60.0) -> None:
        self._tracks: dict[int, TrackHistory] = {}
        self.max_age_seconds = max_age_seconds

    def update(self, track_id: int, class_name: str, cx: float, cy: float,
               timestamp: float | None = None) -> TrackHistory:
        """Record a new centroid observation for a track, creating it if new."""
        ts = timestamp if timestamp is not None else time.time()
        history = self._tracks.get(track_id)
        if history is None:
            history = TrackHistory(track_id=track_id, class_name=class_name)
            self._tracks[track_id] = history
        history.add_point(cx, cy, ts)
        return history

    def get(self, track_id: int) -> TrackHistory | None:
        return self._tracks.get(track_id)

    def prune_stale(self, now: float | None = None) -> int:
        """Remove tracks not updated within max_age_seconds. Returns count removed."""
        now = now if now is not None else time.time()
        stale_ids = [
            tid for tid, h in self._tracks.items()
            if now - h.last_seen > self.max_age_seconds
        ]
        for tid in stale_ids:
            del self._tracks[tid]
        return len(stale_ids)

    def active_track_ids(self) -> list[int]:
        return list(self._tracks.keys())

    def __len__(self) -> int:
        return len(self._tracks)

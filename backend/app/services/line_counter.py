"""
app/services/line_counter.py
--------------------------------------------------------------------
Counts vehicles as they cross a user-configured virtual line (entry
or exit gate), using the sign of the cross-product between the line
and each track's consecutive centroid positions -- the standard,
robust way to detect line crossing regardless of line orientation.

A vehicle is counted exactly once per crossing direction: we track
which side of the line each track_id was last seen on, and only
fire a count event when that side flips.
--------------------------------------------------------------------
"""

from __future__ import annotations

from collections import defaultdict

from app.core.logging import logger
from app.schemas.detection import CountingLineConfig
from app.schemas.tracking import ClassCount, CountingStats


def _side_of_line(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    """
    Cross product of (B-A) x (P-A). Sign tells you which side of the
    line A->B the point P is on. Zero means exactly on the line.
    """
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax)


class LineCounter:
    """Tracks per-line, per-class vehicle counts as tracks cross a virtual line."""

    def __init__(self, config: CountingLineConfig):
        self.config = config
        self._last_side: dict[int, float] = {}       # track_id -> last sign
        self._counted_directions: dict[int, set[str]] = defaultdict(set)  # avoid double count same direction
        self.entry_count = 0
        self.exit_count = 0
        self.by_class: dict[str, int] = defaultdict(int)

    def update(self, track_id: int, class_name: str, cx: float, cy: float) -> str | None:
        """
        Call once per frame per track with its current centroid.
        Returns "entry", "exit", or None if no crossing occurred this call.
        """
        a, b = self.config.point_a, self.config.point_b
        side = _side_of_line(cx, cy, a.x, a.y, b.x, b.y)

        prev_side = self._last_side.get(track_id)
        self._last_side[track_id] = side

        if prev_side is None or side == 0 or prev_side == 0:
            return None  # first observation, or exactly on the line -- can't tell direction yet

        crossed = (prev_side > 0) != (side > 0)
        if not crossed:
            return None

        direction = "entry" if side > prev_side else "exit"
        # Guard against a track flickering across the line boundary and being
        # double-counted in the same direction repeatedly within a short window.
        if direction in self._counted_directions[track_id]:
            return None
        self._counted_directions[track_id] = {direction}  # reset opposite direction eligibility

        if direction == "entry":
            self.entry_count += 1
        else:
            self.exit_count += 1
        self.by_class[class_name] += 1

        logger.debug(f"Line '{self.config.name}': track {track_id} ({class_name}) -> {direction}")
        return direction

    def remove_track(self, track_id: int) -> None:
        """Call when a track is dropped (e.g. left the frame) to free memory."""
        self._last_side.pop(track_id, None)
        self._counted_directions.pop(track_id, None)

    def tracked_ids(self) -> list[int]:
        """IDs this counter currently holds crossing-state for."""
        return list(self._last_side.keys())

    def stats(self, camera_id: str) -> CountingStats:
        return CountingStats(
            camera_id=camera_id,
            total_count=self.entry_count + self.exit_count,
            entry_count=self.entry_count,
            exit_count=self.exit_count,
            by_class=[ClassCount(class_name=k, count=v) for k, v in sorted(self.by_class.items())],
        )

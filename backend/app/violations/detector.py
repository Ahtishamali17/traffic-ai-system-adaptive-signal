"""
app/violations/detector.py
--------------------------------------------------------------------
Rule-based violation detectors that run on top of tracking output
(trajectory history + current position). Each detector is a small,
independently testable class; ViolationEngine composes whichever
ones are configured for a session and emits ViolationEvent objects.

Detectors implemented:
  - WrongDirectionDetector: flags a track moving opposite to the
    configured "correct" traffic flow direction for N consecutive
    samples (avoids false positives from a single noisy frame).
  - LaneViolationDetector: flags a track whose centroid leaves its
    assigned lane polygon.
  - RedLightJumpDetector: flags a track crossing the stop line while
    the (simulated/fed-in) signal state is RED.
  - IllegalUTurnDetector: flags a track whose direction reverses by
    more than ~150 degrees within a short window (an actual U-turn,
    not just weaving).
  - NoParkingDetector: flags a track that stays inside a no-parking
    polygon, near-stationary, longer than a configured duration.

Overspeed violations are NOT duplicated here -- they're already
computed by SpeedEstimator; the session layer converts overspeed
flags into ViolationEvents directly to avoid two sources of truth.
--------------------------------------------------------------------
"""

from __future__ import annotations

import math
import time
from collections import defaultdict

from app.core.logging import logger
from app.schemas.detection import LinePoint
from app.schemas.violations import PolygonZone, TrafficSignalState, ViolationEvent, ViolationType
from app.tracking.trajectory import TrackHistory
from app.utils.geometry import point_in_polygon


class WrongDirectionDetector:
    """Flags vehicles moving opposite to the configured correct-flow direction."""

    def __init__(self, correct_direction_deg: float, tolerance_deg: float = 60.0, min_consecutive: int = 5):
        """
        correct_direction_deg: angle in degrees (0=right, 90=down, 180=left,
            -90/270=up -- image coordinate convention, matching TrackHistory.direction()).
        tolerance_deg: how far from "opposite" still counts as wrong-direction.
        min_consecutive: consecutive wrong-direction samples required before
            flagging, to filter one-frame jitter.
        """
        self.correct_direction_deg = correct_direction_deg % 360
        self.tolerance_deg = tolerance_deg
        self.min_consecutive = min_consecutive
        self._wrong_streak: dict[int, int] = defaultdict(int)
        self._already_flagged: set[int] = set()

    def check(self, history: TrackHistory) -> bool:
        """Returns True exactly once when a track is newly confirmed wrong-direction."""
        if len(history.points) < 2:
            return False

        p_old, p_new = history.points[-2], history.points[-1]
        dx, dy = p_new.x - p_old.x, p_new.y - p_old.y
        if abs(dx) < 3 and abs(dy) < 3:
            return False  # essentially stationary, no reliable direction signal

        actual_deg = math.degrees(math.atan2(dy, dx)) % 360
        opposite_deg = (self.correct_direction_deg + 180) % 360
        diff = min(abs(actual_deg - opposite_deg), 360 - abs(actual_deg - opposite_deg))

        if diff <= self.tolerance_deg:
            self._wrong_streak[history.track_id] += 1
        else:
            self._wrong_streak[history.track_id] = 0

        if (
            self._wrong_streak[history.track_id] >= self.min_consecutive
            and history.track_id not in self._already_flagged
        ):
            self._already_flagged.add(history.track_id)
            return True

        return False

    def remove_track(self, track_id: int) -> None:
        self._wrong_streak.pop(track_id, None)
        self._already_flagged.discard(track_id)


class LaneViolationDetector:
    """Flags a track whose centroid is outside its assigned lane polygon."""

    def __init__(self, lane_polygon: list[LinePoint]):
        self.lane_polygon = lane_polygon
        self._already_flagged: set[int] = set()

    def check(self, track_id: int, cx: float, cy: float) -> bool:
        inside = point_in_polygon(cx, cy, self.lane_polygon)
        if not inside and track_id not in self._already_flagged:
            self._already_flagged.add(track_id)
            return True
        if inside:
            self._already_flagged.discard(track_id)  # re-arm once back in lane
        return False

    def remove_track(self, track_id: int) -> None:
        self._already_flagged.discard(track_id)


class RedLightJumpDetector:
    """
    Flags a track crossing the stop line while the signal is RED.
    Signal state is fed in externally (simulated cycle or real controller
    feed) rather than inferred visually, per the spec's "simulate" note.
    """

    def __init__(self, stop_line_a: LinePoint, stop_line_b: LinePoint):
        self.a, self.b = stop_line_a, stop_line_b
        self._last_side: dict[int, float] = {}
        self._already_flagged: set[int] = set()

    def _side(self, x: float, y: float) -> float:
        ax, ay, bx, by = self.a.x, self.a.y, self.b.x, self.b.y
        return (bx - ax) * (y - ay) - (by - ay) * (x - ax)

    def check(self, track_id: int, cx: float, cy: float, signal_state: TrafficSignalState) -> bool:
        side = self._side(cx, cy)
        prev = self._last_side.get(track_id)
        self._last_side[track_id] = side

        if prev is None or side == 0 or prev == 0:
            return False

        crossed = (prev > 0) != (side > 0)
        if crossed and signal_state == TrafficSignalState.RED and track_id not in self._already_flagged:
            self._already_flagged.add(track_id)
            return True
        return False

    def remove_track(self, track_id: int) -> None:
        self._last_side.pop(track_id, None)
        self._already_flagged.discard(track_id)


class IllegalUTurnDetector:
    """Flags a sharp (>~150 degree) direction reversal within a short time window."""

    def __init__(self, window_seconds: float = 3.0, reversal_threshold_deg: float = 150.0):
        self.window_seconds = window_seconds
        self.reversal_threshold_deg = reversal_threshold_deg
        self._already_flagged: set[int] = set()

    def check(self, history: TrackHistory) -> bool:
        if len(history.points) < 4 or history.track_id in self._already_flagged:
            return False

        now = history.points[-1].timestamp
        recent = [p for p in history.points if now - p.timestamp <= self.window_seconds]
        if len(recent) < 4:
            return False

        early, late = recent[0], recent[len(recent) // 2]
        mid, latest = recent[len(recent) // 2], recent[-1]

        v1 = (late.x - early.x, late.y - early.y)
        v2 = (latest.x - mid.x, latest.y - mid.y)

        mag1 = math.hypot(*v1)
        mag2 = math.hypot(*v2)
        if mag1 < 5 or mag2 < 5:
            return False  # too little movement to judge a turn

        dot = v1[0] * v2[0] + v1[1] * v2[1]
        cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        angle_deg = math.degrees(math.acos(cos_angle))

        if angle_deg >= self.reversal_threshold_deg:
            self._already_flagged.add(history.track_id)
            return True
        return False

    def remove_track(self, track_id: int) -> None:
        self._already_flagged.discard(track_id)


class NoParkingDetector:
    """Flags a track that remains near-stationary inside a no-parking zone too long."""

    def __init__(self, zone: PolygonZone, max_stationary_seconds: float = 30.0, movement_tolerance_px: float = 15.0):
        self.zone = zone
        self.max_stationary_seconds = max_stationary_seconds
        self.movement_tolerance_px = movement_tolerance_px
        self._zone_entry_time: dict[int, float] = {}
        self._already_flagged: set[int] = set()

    def check(self, history: TrackHistory) -> bool:
        if not history.points or history.track_id in self._already_flagged:
            return False

        latest = history.points[-1]
        inside = point_in_polygon(latest.x, latest.y, self.zone.points)

        if not inside:
            self._zone_entry_time.pop(history.track_id, None)
            return False

        entry_time = self._zone_entry_time.setdefault(history.track_id, latest.timestamp)
        duration = latest.timestamp - entry_time

        displacement = math.hypot(
            history.points[-1].x - history.points[0].x,
            history.points[-1].y - history.points[0].y,
        )

        if duration >= self.max_stationary_seconds and displacement <= self.movement_tolerance_px:
            self._already_flagged.add(history.track_id)
            return True
        return False

    def remove_track(self, track_id: int) -> None:
        self._zone_entry_time.pop(track_id, None)
        self._already_flagged.discard(track_id)


class SignalCycleSimulator:
    """
    Cycles a simulated traffic-signal state (RED -> GREEN -> YELLOW -> RED...)
    on a fixed timer, since this system doesn't ingest a real signal
    controller feed. Used to drive RedLightJumpDetector for demo/testing
    purposes, as called for by the "simulate" requirement.
    """

    def __init__(self, red_seconds: float = 10.0, yellow_seconds: float = 3.0, green_seconds: float = 10.0):
        self.durations = {
            TrafficSignalState.RED: red_seconds,
            TrafficSignalState.GREEN: green_seconds,
            TrafficSignalState.YELLOW: yellow_seconds,
        }
        self._cycle_order = [TrafficSignalState.RED, TrafficSignalState.GREEN, TrafficSignalState.YELLOW]
        self._state_index = 0
        self._state_started_at = time.time()

    @property
    def state(self) -> TrafficSignalState:
        current = self._cycle_order[self._state_index]
        elapsed = time.time() - self._state_started_at
        if elapsed >= self.durations[current]:
            self._state_index = (self._state_index + 1) % len(self._cycle_order)
            self._state_started_at = time.time()
            return self._cycle_order[self._state_index]
        return current


class ViolationEngine:
    """Composes whichever detectors are configured and emits ViolationEvents."""

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.wrong_direction: WrongDirectionDetector | None = None
        self.lane_violation: LaneViolationDetector | None = None
        self.red_light: RedLightJumpDetector | None = None
        self.u_turn: IllegalUTurnDetector | None = None
        self.no_parking: NoParkingDetector | None = None
        self.signal_simulator: SignalCycleSimulator | None = None

    @property
    def signal_state(self) -> TrafficSignalState:
        return self.signal_simulator.state if self.signal_simulator else TrafficSignalState.GREEN

    def evaluate(
        self,
        track_id: int,
        class_name: str,
        cx: float,
        cy: float,
        history: TrackHistory,
        bbox,
    ) -> list[ViolationEvent]:
        """Run every configured detector for this track's current state. Returns 0+ events."""
        events: list[ViolationEvent] = []
        now = time.time()

        def emit(v_type: ViolationType, details: str) -> None:
            events.append(
                ViolationEvent(
                    camera_id=self.camera_id, track_id=track_id, class_name=class_name,
                    violation_type=v_type, timestamp=now, bbox=bbox, details=details,
                )
            )

        if self.wrong_direction and self.wrong_direction.check(history):
            emit(ViolationType.WRONG_DIRECTION, "Vehicle moving against configured traffic flow")

        if self.lane_violation and self.lane_violation.check(track_id, cx, cy):
            emit(ViolationType.LANE_VIOLATION, "Vehicle centroid left its assigned lane polygon")

        if self.red_light and self.red_light.check(track_id, cx, cy, self.signal_state):
            emit(ViolationType.RED_LIGHT_JUMP, f"Crossed stop line while signal={self.signal_state}")

        if self.u_turn and self.u_turn.check(history):
            emit(ViolationType.ILLEGAL_U_TURN, "Sharp direction reversal detected")

        if self.no_parking and self.no_parking.check(history):
            emit(ViolationType.NO_PARKING, "Vehicle stationary in no-parking zone beyond limit")

        if events:
            logger.info(f"Camera {self.camera_id}: track {track_id} -> "
                        f"{[e.violation_type.value for e in events]}")
        return events

    def remove_track(self, track_id: int) -> None:
        for detector in (self.wrong_direction, self.lane_violation, self.red_light,
                          self.u_turn, self.no_parking):
            if detector is not None:
                detector.remove_track(track_id)

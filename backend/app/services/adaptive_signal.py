"""
app/services/adaptive_signal.py
--------------------------------------------------------------------
Adaptive traffic signal controller for one intersection with
multiple lanes. Cycles green through each lane in turn, but instead
of a fixed duration (e.g. "60 seconds every time"), each lane's
green duration is computed from its measured vehicle density
relative to the other lanes at the moment its turn begins:

    green_duration = min_green + (density / max_density_across_lanes)
                                  * (max_green - min_green)

So the lane with the most traffic right now gets close to
max_green_seconds; an empty lane gets min_green_seconds; lanes in
between get a proportional share. This directly implements "jis lane
mein traffic zyada hai, us lane ko zyada der green light milegi",
bounded so no lane is ever starved (min_green) or hogs the
intersection forever (max_green).

Density itself is smoothed with an exponential moving average so a
single noisy frame (a car briefly entering/leaving the zone) doesn't
cause the allocated duration to swing wildly between updates that
happen before a lane's green phase actually starts.

This is a pure, dependency-free state machine -- no OpenCV/torch
needed -- so it's fully unit-testable and can be driven by a fake
clock in tests without waiting real seconds.
--------------------------------------------------------------------
"""

from __future__ import annotations

import time

from app.core.logging import logger
from app.schemas.signal import AdaptiveSignalConfig, IntersectionStatus, LaneSignalStatus, SignalPhase


class AdaptiveTrafficController:
    """Cycles green light through lanes, sizing each lane's green duration by relative density."""

    def __init__(self, camera_id: str, config: AdaptiveSignalConfig, clock=time.time):
        if len(config.lanes) < 2:
            raise ValueError("AdaptiveTrafficController needs at least 2 lanes")

        self.camera_id = camera_id
        self.config = config
        self._clock = clock  # injectable for deterministic tests
        self.lane_names = [lane.name for lane in config.lanes]

        self._density: dict[str, float] = {name: 0.0 for name in self.lane_names}
        self._active_index = 0
        self._phase = SignalPhase.GREEN
        self._current_green_duration = config.min_green_seconds
        self._phase_started_at = self._clock()
        self._cycle_count = 0

    # -----------------------------------------------------------------
    # Density input
    # -----------------------------------------------------------------

    def update_density(self, lane_name: str, raw_count: int) -> None:
        """
        Feed the current vehicle count observed inside one lane's polygon
        this frame. Smoothed with an EMA so momentary fluctuations don't
        cause the next-computed green duration to be noisy.
        """
        if lane_name not in self._density:
            return  # unknown lane name, ignore rather than raise mid-session
        alpha = self.config.density_smoothing
        self._density[lane_name] = alpha * raw_count + (1 - alpha) * self._density[lane_name]

    # -----------------------------------------------------------------
    # State machine
    # -----------------------------------------------------------------

    def _active_lane(self) -> str:
        return self.lane_names[self._active_index]

    def _phase_duration(self) -> float:
        if self._phase == SignalPhase.GREEN:
            return self._current_green_duration
        if self._phase == SignalPhase.YELLOW:
            return self.config.yellow_seconds
        return self.config.all_red_seconds  # RED is used as the all-red safety gap here

    def _compute_green_duration(self, lane_name: str) -> float:
        max_density = max(self._density.values()) if self._density else 0.0
        min_g, max_g = self.config.min_green_seconds, self.config.max_green_seconds

        if max_density <= 0:
            return min_g  # no traffic anywhere -- don't reward anyone with extra time

        proportion = self._density[lane_name] / max_density  # 0..1, 1 = busiest lane right now
        return round(min_g + proportion * (max_g - min_g), 1)

    def tick(self, now: float | None = None) -> None:
        """
        Advance the state machine if the current phase has elapsed.
        Call this roughly once per frame/second from the detection loop;
        it's a no-op if the current phase still has time left.
        """
        now = now if now is not None else self._clock()
        elapsed = now - self._phase_started_at
        if elapsed < self._phase_duration():
            return

        if self._phase == SignalPhase.GREEN:
            self._phase = SignalPhase.YELLOW
        elif self._phase == SignalPhase.YELLOW:
            self._phase = SignalPhase.RED  # all-red safety gap
        else:  # RED -> advance to next lane's GREEN
            self._active_index = (self._active_index + 1) % len(self.lane_names)
            self._cycle_count += 1
            next_lane = self._active_lane()
            self._current_green_duration = self._compute_green_duration(next_lane)
            self._phase = SignalPhase.GREEN
            logger.debug(
                f"Intersection {self.camera_id}: lane '{next_lane}' GREEN for "
                f"{self._current_green_duration}s (density={self._density[next_lane]:.1f})"
            )

        self._phase_started_at = now

    # -----------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------

    def get_status(self, now: float | None = None) -> IntersectionStatus:
        now = now if now is not None else self._clock()
        elapsed = now - self._phase_started_at
        remaining = max(0.0, self._phase_duration() - elapsed)
        active = self._active_lane()

        lanes = []
        for name in self.lane_names:
            if name == active:
                phase = self._phase
                lane_remaining = remaining
                green_duration = self._current_green_duration if self._phase == SignalPhase.GREEN else None
            else:
                phase = SignalPhase.RED
                lane_remaining = 0.0
                green_duration = None

            lanes.append(LaneSignalStatus(
                lane_name=name,
                phase=phase,
                remaining_seconds=round(lane_remaining, 1),
                current_density=round(self._density[name], 2),
                current_green_duration=green_duration,
            ))

        return IntersectionStatus(
            camera_id=self.camera_id,
            active_lane=active,
            lanes=lanes,
            cycle_count=self._cycle_count,
        )

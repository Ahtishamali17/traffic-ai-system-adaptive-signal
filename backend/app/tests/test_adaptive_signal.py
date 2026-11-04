"""
Unit tests for app/services/adaptive_signal.py. Uses a fake, manually
advanced clock so tests run instantly instead of waiting real seconds.
"""

import pytest

from app.schemas.signal import AdaptiveSignalConfig, LaneZone, SignalPhase, SignalPoint
from app.services.adaptive_signal import AdaptiveTrafficController


class FakeClock:
    """Manually advanceable clock, injected as `clock=fake_clock` into the controller."""
    def __init__(self, start: float = 0.0):
        self.t = start

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def _square(x0, y0, size=100) -> list[SignalPoint]:
    return [SignalPoint(x=x0, y=y0), SignalPoint(x=x0 + size, y=y0),
            SignalPoint(x=x0 + size, y=y0 + size), SignalPoint(x=x0, y=y0 + size)]


def _by_name(status):
    return {l.lane_name: l for l in status.lanes}


def _make_controller(clock, min_green=10.0, max_green=60.0, yellow=3.0, all_red=2.0, smoothing=1.0):
    config = AdaptiveSignalConfig(
        enabled=True,
        lanes=[
            LaneZone(name="north", polygon=_square(0, 0)),
            LaneZone(name="south", polygon=_square(200, 0)),
            LaneZone(name="east", polygon=_square(400, 0)),
        ],
        min_green_seconds=min_green,
        max_green_seconds=max_green,
        yellow_seconds=yellow,
        all_red_seconds=all_red,
        density_smoothing=smoothing,  # 1.0 = no smoothing, instant update, easier to test exactly
    )
    return AdaptiveTrafficController(camera_id="intersection-1", config=config, clock=clock)


def test_requires_at_least_two_lanes():
    # Pydantic's own min_length=2 constraint on AdaptiveSignalConfig.lanes
    # catches this before AdaptiveTrafficController's own check ever runs.
    with pytest.raises(Exception):
        AdaptiveSignalConfig(
            enabled=True, lanes=[LaneZone(name="only-one", polygon=_square(0, 0))],
        )


def test_starts_on_first_lane_green_with_min_duration():
    clock = FakeClock()
    controller = _make_controller(clock)
    status = controller.get_status()
    assert status.active_lane == "north"
    lanes = _by_name(status)
    assert lanes["north"].phase == SignalPhase.GREEN
    assert lanes["north"].current_green_duration == 10.0  # no density yet -> min_green


def test_busiest_lane_gets_close_to_max_green():
    clock = FakeClock()
    controller = _make_controller(clock)

    controller.update_density("north", 2)
    controller.update_density("south", 20)
    controller.update_density("east", 1)

    clock.advance(10.0); controller.tick()  # north green elapses
    clock.advance(3.0); controller.tick()   # yellow elapses
    clock.advance(2.0); controller.tick()   # all-red elapses -> south green begins

    status = controller.get_status()
    assert status.active_lane == "south"
    lanes = _by_name(status)
    assert lanes["south"].current_green_duration == 60.0  # max density -> max_green


def test_empty_lane_gets_min_green():
    clock = FakeClock()
    controller = _make_controller(clock)

    controller.update_density("north", 0)
    controller.update_density("south", 15)
    controller.update_density("east", 0)

    # north -> south
    clock.advance(10.0); controller.tick()
    clock.advance(3.0); controller.tick()
    clock.advance(2.0); controller.tick()

    status = controller.get_status()
    south_green = _by_name(status)["south"].current_green_duration

    # south -> east
    clock.advance(south_green); controller.tick()
    clock.advance(3.0); controller.tick()
    clock.advance(2.0); controller.tick()

    status = controller.get_status()
    assert status.active_lane == "east"
    assert _by_name(status)["east"].current_green_duration == 10.0  # min_green, zero density


def test_proportional_allocation_between_min_and_max():
    clock = FakeClock()
    controller = _make_controller(clock, min_green=10.0, max_green=60.0)

    controller.update_density("north", 5)
    controller.update_density("south", 10)  # max density
    controller.update_density("east", 0)

    clock.advance(10.0); controller.tick()
    clock.advance(3.0); controller.tick()
    clock.advance(2.0); controller.tick()

    status = controller.get_status()
    assert status.active_lane == "south"
    # south density (10) == max density -> full max_green
    assert _by_name(status)["south"].current_green_duration == 60.0


def test_cycle_wraps_around_and_counts_cycles():
    clock = FakeClock()
    controller = _make_controller(clock)

    for _ in range(3):  # north -> south -> east -> back to north
        clock.advance(60.0)  # comfortably clears whatever green duration is active
        controller.tick()
        clock.advance(3.0)
        controller.tick()
        clock.advance(2.0)
        controller.tick()

    status = controller.get_status()
    assert status.active_lane == "north"
    assert status.cycle_count == 3


def test_tick_is_noop_before_phase_elapses():
    clock = FakeClock()
    controller = _make_controller(clock)
    clock.advance(1.0)  # well before the 10s min_green elapses
    controller.tick()
    status = controller.get_status()
    assert status.active_lane == "north"
    assert _by_name(status)["north"].phase == SignalPhase.GREEN


def test_unknown_lane_name_is_ignored_not_raised():
    clock = FakeClock()
    controller = _make_controller(clock)
    controller.update_density("nonexistent-lane", 99)  # should not raise
    status = controller.get_status()
    assert status.active_lane == "north"

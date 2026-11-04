"""
Unit tests for the tracking-support layer: trajectory history, virtual
line-crossing counting, and speed estimation. These are pure-Python /
numpy-free logic (no torch, no deep-sort-realtime, no OpenCV needed
for the math itself), so they run fast without heavy ML dependencies.
"""

import time

import pytest

from app.schemas.detection import CountingLineConfig, LinePoint
from app.services.line_counter import LineCounter
from app.services.speed_estimator import SpeedEstimator
from app.tracking.trajectory import TrajectoryStore


# ---------------------------------------------------------------------
# TrajectoryStore
# ---------------------------------------------------------------------

def test_trajectory_store_creates_and_updates_track():
    store = TrajectoryStore()
    store.update(track_id=1, class_name="car", cx=10, cy=10, timestamp=100.0)
    store.update(track_id=1, class_name="car", cx=20, cy=10, timestamp=101.0)

    history = store.get(1)
    assert history is not None
    assert history.frames_seen == 2
    assert len(history.points) == 2
    assert history.direction() == "right"


def test_trajectory_store_prunes_stale_tracks():
    store = TrajectoryStore(max_age_seconds=5.0)
    store.update(track_id=1, class_name="car", cx=0, cy=0, timestamp=100.0)
    store.update(track_id=2, class_name="truck", cx=0, cy=0, timestamp=104.0)

    removed = store.prune_stale(now=106.0)  # track 1 is 6s stale, track 2 is 2s stale
    assert removed == 1
    assert store.get(1) is None
    assert store.get(2) is not None


def test_trajectory_direction_stationary_for_tiny_movement():
    store = TrajectoryStore()
    store.update(track_id=1, class_name="car", cx=10.0, cy=10.0, timestamp=1.0)
    store.update(track_id=1, class_name="car", cx=11.0, cy=10.5, timestamp=2.0)
    assert store.get(1).direction() == "stationary"


# ---------------------------------------------------------------------
# LineCounter
# ---------------------------------------------------------------------

def _horizontal_line_at_y(y: int) -> CountingLineConfig:
    return CountingLineConfig(
        name="test-line",
        point_a=LinePoint(x=0, y=y),
        point_b=LinePoint(x=640, y=y),
    )


def test_line_counter_detects_single_crossing():
    counter = LineCounter(_horizontal_line_at_y(240))

    # Track starts above the line, moves below it -> exactly one crossing.
    assert counter.update(track_id=1, class_name="car", cx=100, cy=100) is None  # first obs
    result = counter.update(track_id=1, class_name="car", cx=100, cy=300)
    assert result in ("entry", "exit")
    assert counter.entry_count + counter.exit_count == 1
    assert counter.by_class["car"] == 1


def test_line_counter_does_not_double_count_same_direction():
    counter = LineCounter(_horizontal_line_at_y(240))
    counter.update(track_id=1, class_name="car", cx=100, cy=100)
    counter.update(track_id=1, class_name="car", cx=100, cy=300)  # crosses once
    # Small jitter that stays on the same side should not add another count.
    counter.update(track_id=1, class_name="car", cx=100, cy=310)
    counter.update(track_id=1, class_name="car", cx=100, cy=320)
    assert counter.entry_count + counter.exit_count == 1


def test_line_counter_counts_opposite_direction_separately():
    counter = LineCounter(_horizontal_line_at_y(240))
    counter.update(track_id=1, class_name="car", cx=100, cy=100)
    first = counter.update(track_id=1, class_name="car", cx=100, cy=300)  # cross down
    second = counter.update(track_id=1, class_name="car", cx=100, cy=100)  # cross back up
    assert first != second
    assert counter.entry_count == 1
    assert counter.exit_count == 1


def test_line_counter_no_crossing_when_staying_on_one_side():
    counter = LineCounter(_horizontal_line_at_y(240))
    counter.update(track_id=1, class_name="car", cx=100, cy=100)
    result = counter.update(track_id=1, class_name="car", cx=100, cy=110)
    assert result is None
    assert counter.entry_count == 0 and counter.exit_count == 0


def test_line_counter_stats_output():
    counter = LineCounter(_horizontal_line_at_y(240))
    counter.update(track_id=1, class_name="car", cx=100, cy=100)
    counter.update(track_id=1, class_name="car", cx=100, cy=300)
    stats = counter.stats(camera_id="gate-1")
    assert stats.camera_id == "gate-1"
    assert stats.total_count == 1
    assert stats.by_class[0].class_name == "car"


# ---------------------------------------------------------------------
# SpeedEstimator
# ---------------------------------------------------------------------

def test_speed_estimator_returns_none_with_insufficient_history():
    store = TrajectoryStore()
    store.update(track_id=1, class_name="car", cx=0, cy=0, timestamp=100.0)
    estimator = SpeedEstimator(pixels_per_meter=10.0, speed_limit_kmph=60.0)
    speed, avg, overspeed = estimator.estimate(store.get(1))
    assert speed is None and avg is None and overspeed is False


def test_speed_estimator_computes_reasonable_speed():
    store = TrajectoryStore()
    # 100 pixels in 1 second, 10 pixels/meter -> 10 m/s -> 36 km/h
    store.update(track_id=1, class_name="car", cx=0, cy=0, timestamp=100.0)
    store.update(track_id=1, class_name="car", cx=100, cy=0, timestamp=101.0)

    estimator = SpeedEstimator(pixels_per_meter=10.0, speed_limit_kmph=60.0)
    speed, avg, overspeed = estimator.estimate(store.get(1))

    assert speed == pytest.approx(36.0, abs=0.5)
    assert avg == pytest.approx(36.0, abs=0.5)
    assert overspeed is False


def test_speed_estimator_flags_overspeed():
    store = TrajectoryStore()
    # 200 pixels in 1 second, 10 pixels/meter -> 20 m/s -> 72 km/h
    store.update(track_id=1, class_name="car", cx=0, cy=0, timestamp=100.0)
    store.update(track_id=1, class_name="car", cx=200, cy=0, timestamp=101.0)

    estimator = SpeedEstimator(pixels_per_meter=10.0, speed_limit_kmph=60.0)
    _, avg, overspeed = estimator.estimate(store.get(1))

    assert avg > 60.0
    assert overspeed is True


def test_speed_estimator_rejects_invalid_calibration():
    with pytest.raises(ValueError):
        SpeedEstimator(pixels_per_meter=0, speed_limit_kmph=60.0)

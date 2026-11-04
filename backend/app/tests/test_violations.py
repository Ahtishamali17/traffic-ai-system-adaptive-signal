"""
Unit tests for app/violations/detector.py -- all pure Python logic,
no torch/opencv/deep-sort required.
"""

from app.schemas.detection import LinePoint
from app.schemas.violations import PolygonZone, TrafficSignalState
from app.tracking.trajectory import TrajectoryStore
from app.violations.detector import (
    IllegalUTurnDetector,
    LaneViolationDetector,
    NoParkingDetector,
    RedLightJumpDetector,
    WrongDirectionDetector,
)


def test_wrong_direction_flags_after_min_consecutive():
    store = TrajectoryStore()
    detector = WrongDirectionDetector(correct_direction_deg=0, min_consecutive=3)  # correct = moving right

    flagged = False
    x = 100
    for i in range(5):
        store.update(track_id=1, class_name="car", cx=x, cy=100, timestamp=float(i))
        x -= 20  # moving LEFT == wrong direction (opposite of correct=right)
        flagged = flagged or detector.check(store.get(1))

    assert flagged is True


def test_wrong_direction_does_not_flag_correct_direction():
    store = TrajectoryStore()
    detector = WrongDirectionDetector(correct_direction_deg=0, min_consecutive=3)

    flagged = False
    x = 100
    for i in range(5):
        store.update(track_id=1, class_name="car", cx=x, cy=100, timestamp=float(i))
        x += 20  # moving RIGHT == correct direction
        flagged = flagged or detector.check(store.get(1))

    assert flagged is False


def test_lane_violation_detects_exit_from_polygon():
    square = [LinePoint(x=0, y=0), LinePoint(x=100, y=0), LinePoint(x=100, y=100), LinePoint(x=0, y=100)]
    detector = LaneViolationDetector(lane_polygon=square)

    assert detector.check(track_id=1, cx=50, cy=50) is False  # inside
    assert detector.check(track_id=1, cx=200, cy=200) is True  # left the lane
    assert detector.check(track_id=1, cx=200, cy=200) is False  # already flagged, no repeat


def test_red_light_jump_only_flags_on_red():
    line_a, line_b = LinePoint(x=0, y=200), LinePoint(x=640, y=200)
    detector = RedLightJumpDetector(line_a, line_b)

    detector.check(track_id=1, cx=100, cy=100, signal_state=TrafficSignalState.RED)  # first obs, above line
    result_green = detector.check(track_id=1, cx=100, cy=300, signal_state=TrafficSignalState.GREEN)
    assert result_green is False

    detector2 = RedLightJumpDetector(line_a, line_b)
    detector2.check(track_id=2, cx=100, cy=100, signal_state=TrafficSignalState.RED)
    result_red = detector2.check(track_id=2, cx=100, cy=300, signal_state=TrafficSignalState.RED)
    assert result_red is True


def test_illegal_u_turn_detects_sharp_reversal():
    store = TrajectoryStore()
    detector = IllegalUTurnDetector(window_seconds=5.0, reversal_threshold_deg=150.0)

    store.update(track_id=1, class_name="car", cx=0, cy=100, timestamp=0.0)
    store.update(track_id=1, class_name="car", cx=50, cy=100, timestamp=1.0)
    store.update(track_id=1, class_name="car", cx=100, cy=100, timestamp=2.0)
    store.update(track_id=1, class_name="car", cx=50, cy=100, timestamp=3.0)
    result = detector.check(store.get(1))
    store.update(track_id=1, class_name="car", cx=0, cy=100, timestamp=4.0)
    result = result or detector.check(store.get(1))

    assert result is True


def test_illegal_u_turn_not_flagged_for_straight_travel():
    store = TrajectoryStore()
    detector = IllegalUTurnDetector(window_seconds=5.0, reversal_threshold_deg=150.0)

    flagged = False
    for i in range(5):
        store.update(track_id=1, class_name="car", cx=i * 20, cy=100, timestamp=float(i))
        flagged = flagged or detector.check(store.get(1))

    assert flagged is False


def test_no_parking_flags_after_duration_threshold():
    zone = PolygonZone(
        name="no-park",
        points=[LinePoint(x=0, y=0), LinePoint(x=100, y=0), LinePoint(x=100, y=100), LinePoint(x=0, y=100)],
    )
    store = TrajectoryStore()
    detector = NoParkingDetector(zone, max_stationary_seconds=10.0, movement_tolerance_px=15.0)

    flagged = False
    for i in range(0, 15, 2):
        store.update(track_id=1, class_name="car", cx=50, cy=50, timestamp=float(i))
        flagged = flagged or detector.check(store.get(1))

    assert flagged is True


def test_no_parking_not_flagged_if_vehicle_leaves_zone():
    zone = PolygonZone(
        name="no-park",
        points=[LinePoint(x=0, y=0), LinePoint(x=100, y=0), LinePoint(x=100, y=100), LinePoint(x=0, y=100)],
    )
    store = TrajectoryStore()
    detector = NoParkingDetector(zone, max_stationary_seconds=10.0)

    store.update(track_id=1, class_name="car", cx=50, cy=50, timestamp=0.0)
    detector.check(store.get(1))
    store.update(track_id=1, class_name="car", cx=500, cy=500, timestamp=5.0)
    flagged = detector.check(store.get(1))

    assert flagged is False

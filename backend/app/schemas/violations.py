"""
app/schemas/violations.py
--------------------------------------------------------------------
Wire + storage models for traffic violation events.
--------------------------------------------------------------------
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from app.schemas.detection import BoundingBox, LinePoint


class ViolationType(str, Enum):
    WRONG_DIRECTION = "wrong_direction"
    LANE_VIOLATION = "lane_violation"
    OVERSPEED = "overspeed"
    RED_LIGHT_JUMP = "red_light_jump"
    ILLEGAL_U_TURN = "illegal_u_turn"
    NO_PARKING = "no_parking"


class ViolationEvent(BaseModel):
    camera_id: str
    track_id: int
    class_name: str
    violation_type: ViolationType
    timestamp: float
    bbox: BoundingBox
    details: str = ""
    speed_kmph: float | None = None


class PolygonZone(BaseModel):
    """A named polygon region (ROI, no-parking zone, lane, etc.) in frame-pixel coords."""
    name: str
    points: list[LinePoint]  # at least 3 points


class TrafficSignalState(str, Enum):
    """Simulated signal state -- real deployments would feed this from a
    signal controller; here it can be toggled manually via the API or
    cycled on a timer for demo purposes."""
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"

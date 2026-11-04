"""
app/schemas/signal.py
--------------------------------------------------------------------
Wire models for adaptive traffic signal control: one intersection
with multiple lanes, each a polygon zone within the camera frame.
Green-light duration for each lane adapts to that lane's measured
vehicle density -- busier lanes get more green time, within
configured min/max bounds.
--------------------------------------------------------------------
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SignalPhase(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class SignalPoint(BaseModel):
    """A point in frame-pixel coordinates. Kept local to this module (rather
    than importing detection.LinePoint) so app.schemas.detection can import
    AdaptiveSignalConfig from here without a circular import."""
    x: int
    y: int


class LaneZone(BaseModel):
    """One lane's polygon region within the frame, for density measurement."""
    name: str
    polygon: list[SignalPoint] = Field(..., description="3+ points defining this lane's area")


class AdaptiveSignalConfig(BaseModel):
    """Configuration for adaptive multi-lane signal control at one intersection."""
    enabled: bool = False
    lanes: list[LaneZone] = Field(..., min_length=2, description="At least 2 lanes to cycle between")
    min_green_seconds: float = Field(10.0, gt=0)
    max_green_seconds: float = Field(60.0, gt=0)
    yellow_seconds: float = Field(3.0, gt=0)
    all_red_seconds: float = Field(2.0, ge=0, description="Safety gap between one lane's yellow and the next lane's green")
    density_smoothing: float = Field(
        0.3, ge=0.0, le=1.0,
        description="EMA smoothing factor for density (0=very smooth/slow to react, 1=instant/noisy)",
    )


class LaneSignalStatus(BaseModel):
    lane_name: str
    phase: SignalPhase
    remaining_seconds: float
    current_density: float
    current_green_duration: float | None = None  # only meaningful while this lane is GREEN


class IntersectionStatus(BaseModel):
    camera_id: str
    active_lane: str
    lanes: list[LaneSignalStatus]
    cycle_count: int

"""
app/schemas/tracking.py
--------------------------------------------------------------------
Wire models for the tracking layer: a tracked vehicle (detection +
permanent ID + speed/direction), its path history, and virtual-line
counting statistics.
--------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.detection import BoundingBox, CountingLineConfig, LinePoint

__all__ = [
    "TrackPoint", "TrackedVehicle", "LinePoint", "CountingLineConfig",
    "ClassCount", "CountingStats",
]


class TrackPoint(BaseModel):
    """One sample of a vehicle's centroid position over time."""
    x: float
    y: float
    timestamp: float  # unix epoch seconds


class TrackedVehicle(BaseModel):
    """A single vehicle with a permanent tracking ID, for one frame."""
    track_id: int
    class_name: str
    confidence: float
    bbox: BoundingBox
    speed_kmph: float | None = None
    avg_speed_kmph: float | None = None
    direction: str | None = None  # "inbound" | "outbound" | "left" | "right" | "stationary"
    age_frames: int = Field(..., description="Frames since this track was first seen")
    path_length: int = Field(..., description="Number of trajectory points retained")


class ClassCount(BaseModel):
    class_name: str
    count: int


class CountingStats(BaseModel):
    camera_id: str
    total_count: int
    entry_count: int
    exit_count: int
    by_class: list[ClassCount]
    peak_hour: str | None = None

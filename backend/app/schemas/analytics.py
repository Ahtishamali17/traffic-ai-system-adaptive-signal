"""
app/schemas/analytics.py
--------------------------------------------------------------------
Wire models for the analytics/reporting API.
--------------------------------------------------------------------
"""

from __future__ import annotations

from pydantic import BaseModel


class HourlyCount(BaseModel):
    hour: str  # "2026-08-22 14:00"
    count: int


class DailyCount(BaseModel):
    date: str  # "2026-08-22"
    count: int


class ClassBreakdown(BaseModel):
    class_name: str
    count: int
    percentage: float


class PeakHour(BaseModel):
    hour: str
    count: int


class AnalyticsSummary(BaseModel):
    camera_id: str | None  # None = all cameras
    period_start: str
    period_end: str
    total_vehicles: int
    hourly_counts: list[HourlyCount]
    daily_counts: list[DailyCount]
    class_breakdown: list[ClassBreakdown]
    peak_hour: PeakHour | None
    total_violations: int
    violations_by_type: dict[str, int]

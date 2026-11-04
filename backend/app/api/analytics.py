"""
app/api/analytics.py
--------------------------------------------------------------------
REST API for traffic analytics:
  GET /api/v1/analytics/summary - full analytics summary (counts,
                                   class breakdown, peak hour, violations)
--------------------------------------------------------------------
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.schemas.analytics import AnalyticsSummary
from app.services.analytics_service import build_summary

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    camera_id: str | None = Query(None, description="Filter to one camera; omit for all cameras"),
    days: int = Query(7, ge=1, le=90, description="Trailing window size in days"),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> AnalyticsSummary:
    """
    Hourly/daily vehicle counts, class distribution, peak traffic hour,
    and violation totals over the trailing `days` days.
    """
    return await build_summary(db, camera_id=camera_id, days=days)

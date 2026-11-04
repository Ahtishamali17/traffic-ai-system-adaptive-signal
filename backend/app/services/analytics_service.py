"""
app/services/analytics_service.py
--------------------------------------------------------------------
Builds traffic analytics (hourly/daily counts, class distribution,
peak hour, violation stats) from the `vehicle_events` and
`violations` collections written by app/services/event_store.py.

Uses the async Motor client (this runs inside normal FastAPI request
handlers, not a background detection thread, so async is fine and
preferred here).
--------------------------------------------------------------------
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.analytics import AnalyticsSummary, ClassBreakdown, DailyCount, HourlyCount, PeakHour


async def _match_stage(camera_id: str | None, start_ts: float, end_ts: float) -> dict:
    match: dict = {"timestamp": {"$gte": start_ts, "$lte": end_ts}}
    if camera_id:
        match["camera_id"] = camera_id
    return match


async def get_hourly_counts(db: AsyncIOMotorDatabase, camera_id: str | None, start_ts: float, end_ts: float) -> list[HourlyCount]:
    match = await _match_stage(camera_id, start_ts, end_ts)
    pipeline = [
        {"$match": match},
        {"$addFields": {"hour_bucket": {
            "$dateToString": {"format": "%Y-%m-%d %H:00", "date": {"$toDate": {"$multiply": ["$timestamp", 1000]}}}
        }}},
        {"$group": {"_id": "$hour_bucket", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    results = await db.vehicle_events.aggregate(pipeline).to_list(length=None)
    return [HourlyCount(hour=r["_id"], count=r["count"]) for r in results]


async def get_daily_counts(db: AsyncIOMotorDatabase, camera_id: str | None, start_ts: float, end_ts: float) -> list[DailyCount]:
    match = await _match_stage(camera_id, start_ts, end_ts)
    pipeline = [
        {"$match": match},
        {"$addFields": {"day_bucket": {
            "$dateToString": {"format": "%Y-%m-%d", "date": {"$toDate": {"$multiply": ["$timestamp", 1000]}}}
        }}},
        {"$group": {"_id": "$day_bucket", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    results = await db.vehicle_events.aggregate(pipeline).to_list(length=None)
    return [DailyCount(date=r["_id"], count=r["count"]) for r in results]


async def get_class_breakdown(db: AsyncIOMotorDatabase, camera_id: str | None, start_ts: float, end_ts: float) -> list[ClassBreakdown]:
    match = await _match_stage(camera_id, start_ts, end_ts)
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$class_name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    results = await db.vehicle_events.aggregate(pipeline).to_list(length=None)
    total = sum(r["count"] for r in results) or 1
    return [
        ClassBreakdown(class_name=r["_id"], count=r["count"], percentage=round(100 * r["count"] / total, 1))
        for r in results
    ]


async def get_peak_hour(hourly_counts: list[HourlyCount]) -> PeakHour | None:
    if not hourly_counts:
        return None
    top = max(hourly_counts, key=lambda h: h.count)
    return PeakHour(hour=top.hour, count=top.count)


async def get_violation_stats(db: AsyncIOMotorDatabase, camera_id: str | None, start_ts: float, end_ts: float) -> tuple[int, dict[str, int]]:
    match = await _match_stage(camera_id, start_ts, end_ts)
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$violation_type", "count": {"$sum": 1}}},
    ]
    results = await db.violations.aggregate(pipeline).to_list(length=None)
    by_type = {r["_id"]: r["count"] for r in results}
    return sum(by_type.values()), by_type


async def build_summary(
    db: AsyncIOMotorDatabase, camera_id: str | None = None, days: int = 7,
) -> AnalyticsSummary:
    """Assembles the full analytics summary for the trailing `days` days."""
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)
    start_ts, end_ts = start_dt.timestamp(), end_dt.timestamp()

    hourly = await get_hourly_counts(db, camera_id, start_ts, end_ts)
    daily = await get_daily_counts(db, camera_id, start_ts, end_ts)
    breakdown = await get_class_breakdown(db, camera_id, start_ts, end_ts)
    peak = await get_peak_hour(hourly)
    total_violations, violations_by_type = await get_violation_stats(db, camera_id, start_ts, end_ts)

    total_vehicles = sum(d.count for d in daily)

    return AnalyticsSummary(
        camera_id=camera_id,
        period_start=start_dt.strftime("%Y-%m-%d %H:%M"),
        period_end=end_dt.strftime("%Y-%m-%d %H:%M"),
        total_vehicles=total_vehicles,
        hourly_counts=hourly,
        daily_counts=daily,
        class_breakdown=breakdown,
        peak_hour=peak,
        total_violations=total_violations,
        violations_by_type=violations_by_type,
    )

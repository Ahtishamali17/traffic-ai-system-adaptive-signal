"""
app/services/event_store.py
--------------------------------------------------------------------
Writes vehicle count/crossing events and violation events to MongoDB
from inside detection session background threads, using the
synchronous pymongo client (see app/core/database.get_sync_database).

Kept as a thin wrapper so the detection loop never touches pymongo
directly, and so this is the one place that would change if we
later moved to a message queue instead of direct DB writes.
--------------------------------------------------------------------
"""

from __future__ import annotations

from app.core.database import get_sync_database
from app.core.logging import logger
from app.schemas.tracking import CountingStats
from app.schemas.violations import ViolationEvent


def save_violation(event: ViolationEvent) -> None:
    """Persist one violation event. Never raises -- a DB hiccup must not crash detection."""
    try:
        db = get_sync_database()
        db.violations.insert_one(event.model_dump())
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to persist violation event: {exc}")


def save_vehicle_crossing_event(
    camera_id: str, track_id: int, class_name: str, direction: str, timestamp: float,
) -> None:
    """Persist one entry/exit line-crossing event, used later for hourly/daily analytics."""
    try:
        db = get_sync_database()
        db.vehicle_events.insert_one({
            "camera_id": camera_id,
            "track_id": track_id,
            "class_name": class_name,
            "direction": direction,
            "timestamp": timestamp,
        })
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to persist vehicle crossing event: {exc}")


def save_session_summary(camera_id: str, session_id: str, stats: CountingStats) -> None:
    """Upsert the latest counting summary for a session (used by the analytics dashboard)."""
    try:
        db = get_sync_database()
        db.sessions.update_one(
            {"session_id": session_id},
            {"$set": {
                "camera_id": camera_id,
                "session_id": session_id,
                "total_count": stats.total_count,
                "entry_count": stats.entry_count,
                "exit_count": stats.exit_count,
                "by_class": [c.model_dump() for c in stats.by_class],
            }},
            upsert=True,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to persist session summary: {exc}")

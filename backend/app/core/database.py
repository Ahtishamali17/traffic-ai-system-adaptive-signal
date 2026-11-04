"""
app/core/database.py
--------------------------------------------------------------------
Async MongoDB connection lifecycle management using Motor.

FastAPI's startup/shutdown events call `connect_to_mongo()` and
`close_mongo_connection()` so we open one connection pool for the
life of the app instead of reconnecting per-request.
--------------------------------------------------------------------
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()


class MongoManager:
    """Holds the single Motor client/database instance for the app."""

    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


mongo_manager = MongoManager()


async def connect_to_mongo() -> None:
    """Open the MongoDB connection pool. Called on FastAPI startup."""
    try:
        mongo_manager.client = AsyncIOMotorClient(settings.MONGO_URI)
        mongo_manager.db = mongo_manager.client[settings.MONGO_DB_NAME]
        # The ping command is cheap and confirms the server is reachable.
        await mongo_manager.client.admin.command("ping")
        logger.info(f"Connected to MongoDB at {settings.MONGO_URI}")
        await _ensure_indexes()
    except Exception as exc:
        logger.error(f"Failed to connect to MongoDB: {exc}")
        raise


async def close_mongo_connection() -> None:
    """Close the MongoDB connection pool. Called on FastAPI shutdown."""
    if mongo_manager.client:
        mongo_manager.client.close()
        logger.info("MongoDB connection closed")


async def _ensure_indexes() -> None:
    """Create indexes needed for query performance (idempotent)."""
    db = mongo_manager.db
    assert db is not None

    await db.vehicle_events.create_index("track_id")
    await db.vehicle_events.create_index("timestamp")
    await db.vehicle_events.create_index([("camera_id", 1), ("timestamp", -1)])

    await db.violations.create_index("timestamp")
    await db.violations.create_index("violation_type")

    await db.sessions.create_index("camera_id")

    logger.debug("MongoDB indexes ensured")


def get_database() -> AsyncIOMotorDatabase:
    """
    FastAPI dependency: yields the shared database instance.

    Usage in a route:
        async def endpoint(db = Depends(get_database)): ...
    """
    assert mongo_manager.db is not None, "Database not initialized"
    return mongo_manager.db


# ---------------------------------------------------------------------
# Synchronous client for background threads (detection sessions run in
# their own threads, not the asyncio event loop -- see
# app/services/detection_session.py -- so they can't safely use the
# async Motor client without extra event-loop plumbing. A small,
# separate pymongo client is simpler and perfectly fine for the
# comparatively low write volume of violation/vehicle events.)
# ---------------------------------------------------------------------
_sync_client: MongoClient | None = None


def get_sync_database() -> Database:
    """Lazily create and return a synchronous pymongo database handle."""
    global _sync_client
    if _sync_client is None:
        _sync_client = MongoClient(settings.MONGO_URI)
        logger.debug("Synchronous MongoDB client created (for background threads)")
    return _sync_client[settings.MONGO_DB_NAME]

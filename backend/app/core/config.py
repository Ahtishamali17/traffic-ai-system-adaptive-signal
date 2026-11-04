"""
app/core/config.py
--------------------------------------------------------------------
Centralized, type-safe application configuration.

All values are loaded from environment variables (via a `.env` file
in development, or real environment variables in production/Docker).
Nothing is hardcoded so the same codebase runs unchanged across
dev / staging / production.
--------------------------------------------------------------------
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings, populated from environment variables."""

    # ---------------------------------------------------------------
    # General
    # ---------------------------------------------------------------
    APP_NAME: str = "AI Traffic Monitoring System"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # ---------------------------------------------------------------
    # Server
    # ---------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ---------------------------------------------------------------
    # CORS
    # ---------------------------------------------------------------
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",
    ]

    # ---------------------------------------------------------------
    # Database (MongoDB)
    # ---------------------------------------------------------------
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "traffic_monitoring"

    # ---------------------------------------------------------------
    # AI Model / Detection
    # ---------------------------------------------------------------
    MODEL_WEIGHTS_PATH: str = "models/weights/yolov8n.pt"
    DEVICE: str = "cpu"  # cpu | cuda | mps
    CONFIDENCE_THRESHOLD: float = 0.4
    IOU_THRESHOLD: float = 0.45
    FRAME_SKIP: int = 1          # process every Nth frame
    MAX_TRACK_AGE: int = 30      # frames before a lost track is dropped

    # Vehicle classes the system cares about (subset of COCO + custom)
    VEHICLE_CLASSES: List[str] = [
        "car", "truck", "bus", "motorcycle", "bicycle",
        "auto_rickshaw", "van", "emergency_vehicle",
    ]

    # ---------------------------------------------------------------
    # Storage
    # ---------------------------------------------------------------
    UPLOAD_DIR: str = "storage/uploads"
    REPORT_DIR: str = "storage/reports"
    SNAPSHOT_DIR: str = "storage/snapshots"

    # ---------------------------------------------------------------
    # Alerts
    # ---------------------------------------------------------------
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    ALERT_EMAIL_FROM: str = ""
    ALERT_EMAIL_TO: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    # ---------------------------------------------------------------
    # Speed / Violation thresholds
    # ---------------------------------------------------------------
    SPEED_LIMIT_KMPH: float = 60.0
    PIXELS_PER_METER: float = 8.0  # calibration constant, camera-specific

    # ---------------------------------------------------------------
    # Security
    # ---------------------------------------------------------------
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> "Settings":
    """
    Cached settings accessor.

    Using lru_cache ensures the .env file is parsed only once and the
    same Settings instance is reused across the app (cheap DI pattern
    for FastAPI's `Depends(get_settings)`).
    """
    return Settings()


def ensure_storage_dirs() -> None:
    """Create storage directories on startup if they don't exist yet."""
    settings = get_settings()
    for path in (settings.UPLOAD_DIR, settings.REPORT_DIR, settings.SNAPSHOT_DIR):
        Path(path).mkdir(parents=True, exist_ok=True)

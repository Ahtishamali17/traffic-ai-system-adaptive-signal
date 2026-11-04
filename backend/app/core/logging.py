"""
app/core/logging.py
--------------------------------------------------------------------
Centralized logging configuration using loguru.

Production systems need structured, leveled, rotated logs -- not
scattered print() statements. This module configures a single
logger instance that every module in the app imports and reuses.
--------------------------------------------------------------------
"""

import sys
from pathlib import Path

from loguru import logger

from app.core.config import get_settings

settings = get_settings()

LOG_DIR = Path("storage/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


def configure_logging() -> None:
    """Configure loguru sinks (console + rotating file)."""
    logger.remove()  # remove default handler

    # Console sink: human-readable, colorized
    logger.add(
        sys.stdout,
        level="DEBUG" if settings.DEBUG else "INFO",
        colorize=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
            "- <level>{message}</level>"
        ),
    )

    # File sink: rotated daily, retained for 14 days, JSON-free plain text
    logger.add(
        LOG_DIR / "app.log",
        level="INFO",
        rotation="00:00",
        retention="14 days",
        compression="zip",
        enqueue=True,  # thread/process-safe logging
        backtrace=True,
        diagnose=False,  # avoid leaking variable values in production logs
    )


# Export a ready-to-use logger for other modules: `from app.core.logging import logger`
__all__ = ["logger", "configure_logging"]

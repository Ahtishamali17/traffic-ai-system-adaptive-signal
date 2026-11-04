"""
app/services/alerts.py
--------------------------------------------------------------------
Dispatches real-world notifications (Telegram, email) when a
violation or other alert-worthy condition fires: overspeed, wrong
direction, a crowded area, or a "suspicious" (loitering) vehicle.

Design notes:
  - Both channels are optional and independently configured; if
    credentials aren't set in Settings, that channel is silently
    skipped (not an error -- most deployments will only use one).
  - Per (camera_id, alert_key) rate limiting prevents the same
    condition from spamming notifications every frame while it
    persists (e.g. a vehicle sitting 5 km/h over the limit for 10
    seconds shouldn't send 300 messages).
  - Runs inside the detection session's background thread, so both
    senders are synchronous (blocking network I/O here is fine --
    it's already off the async event loop). Telegram uses `httpx`
    already in requirements.txt; email uses the stdlib `smtplib`
    for the same reason (no event loop to await on in this thread).
--------------------------------------------------------------------
"""

from __future__ import annotations

import smtplib
import time
from email.mime.text import MIMEText
from enum import Enum

import httpx

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

RATE_LIMIT_SECONDS = 60.0  # minimum gap between repeat alerts for the same (camera, key)


class AlertKind(str, Enum):
    OVERSPEED = "overspeed"
    WRONG_DIRECTION = "wrong_direction"
    CROWDED_AREA = "crowded_area"
    SUSPICIOUS_VEHICLE = "suspicious_vehicle"
    VIOLATION = "violation"  # generic bucket for lane/red-light/u-turn/no-parking


class AlertService:
    """Stateful dispatcher: holds rate-limit timestamps across calls for one process."""

    def __init__(self) -> None:
        self._last_sent: dict[tuple[str, str], float] = {}

    def _rate_limited(self, camera_id: str, key: str) -> bool:
        now = time.time()
        last = self._last_sent.get((camera_id, key))
        if last is not None and now - last < RATE_LIMIT_SECONDS:
            return True
        self._last_sent[(camera_id, key)] = now
        return False

    def send(self, camera_id: str, kind: AlertKind, message: str) -> None:
        """Send an alert through every configured channel, honoring rate limits."""
        if self._rate_limited(camera_id, kind.value):
            return

        full_message = f"[{settings.APP_NAME}] {camera_id}: {message}"
        logger.info(f"ALERT ({kind.value}): {full_message}")

        self._send_telegram(full_message)
        self._send_email(subject=f"Traffic Alert: {kind.value}", body=full_message)

    def _send_telegram(self, message: str) -> None:
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
            return  # channel not configured, skip silently
        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        try:
            resp = httpx.post(
                url, json={"chat_id": settings.TELEGRAM_CHAT_ID, "text": message}, timeout=5.0,
            )
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001 - alert failures must never crash detection
            logger.error(f"Telegram alert failed: {exc}")

    def _send_email(self, subject: str, body: str) -> None:
        if not (settings.SMTP_HOST and settings.ALERT_EMAIL_FROM and settings.ALERT_EMAIL_TO):
            return  # channel not configured, skip silently
        try:
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = settings.ALERT_EMAIL_FROM
            msg["To"] = settings.ALERT_EMAIL_TO

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=5) as server:
                server.starttls()
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Email alert failed: {exc}")


# Process-wide singleton so rate-limit state is shared across all sessions.
alert_service = AlertService()

"""Daily library rotation at a fixed local time (HHMM)."""

from __future__ import annotations

import logging
import re
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import DAILY_CHANGE_TIME, TZ_NAME
from frame_service import change_frame

logger = logging.getLogger(__name__)

_HHMM_RE = re.compile(r"^(\d{2})(\d{2})$")
_DEFAULT_HHMM = "0300"

_started = False
_start_lock = threading.Lock()


def parse_daily_change_time(value: str | None) -> tuple[int, int]:
    """Parse HHMM (e.g. 0300) into (hour, minute). Invalid values default to 03:00."""
    raw = str(value or _DEFAULT_HHMM).strip()
    match = _HHMM_RE.match(raw)
    if not match:
        return 3, 0

    hour = int(match.group(1))
    minute = int(match.group(2))
    if hour > 23 or minute > 59:
        return 3, 0
    return hour, minute


def seconds_until_next_run(
    hour: int,
    minute: int,
    *,
    now: datetime | None = None,
    tz: ZoneInfo | None = None,
) -> float:
    """Seconds until the next occurrence of hour:minute in the given timezone."""
    zone = tz or ZoneInfo(TZ_NAME)
    current = now.astimezone(zone) if now else datetime.now(zone)
    target = current.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= current:
        target += timedelta(days=1)
    return (target - current).total_seconds()


def _daily_loop() -> None:
    hour, minute = parse_daily_change_time(DAILY_CHANGE_TIME)
    tz = ZoneInfo(TZ_NAME)
    logger.info(
        "Daily frame change enabled at %02d:%02d (%s)",
        hour,
        minute,
        TZ_NAME,
    )

    while True:
        wait_seconds = seconds_until_next_run(hour, minute, tz=tz)
        next_at = datetime.now(tz) + timedelta(seconds=wait_seconds)
        logger.info(
            "Next daily frame change at %s (in %.0f s)",
            next_at.strftime("%Y-%m-%d %H:%M:%S %Z"),
            wait_seconds,
        )
        time.sleep(wait_seconds)

        try:
            name = change_frame()
            if name:
                logger.info("Daily frame change completed: %s", name)
            else:
                logger.warning("Daily frame change skipped: library is empty")
        except Exception:
            logger.exception("Daily frame change failed")


def start() -> None:
    """Start the background daily scheduler thread (idempotent)."""
    global _started
    with _start_lock:
        if _started:
            return
        thread = threading.Thread(target=_daily_loop, name="daily-scheduler", daemon=True)
        thread.start()
        _started = True

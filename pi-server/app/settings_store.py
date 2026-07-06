"""Runtime settings persisted alongside library state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import DATA_DIR, DITHER_METHOD, DRIVER_WAKE_INTERVAL_SECONDS

SETTINGS_PATH = Path(DATA_DIR) / "settings.json"

_SETTING_KEYS = ("default_dither_method", "last_driver_fetch_at")


def _default_settings() -> dict:
    return {
        "default_dither_method": DITHER_METHOD,
        "last_driver_fetch_at": None,
    }


def load_settings() -> dict:
    if not SETTINGS_PATH.is_file():
        return _default_settings()
    data = json.loads(SETTINGS_PATH.read_text())
    base = _default_settings()
    base.update({k: v for k, v in data.items() if k in _SETTING_KEYS})
    return base


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


def get_default_dither_method() -> str:
    method = str(load_settings()["default_dither_method"]).lower()
    return method if method in ("floyd_steinberg", "atkinson") else "floyd_steinberg"


def set_default_dither_method(method: str) -> None:
    method = method.lower()
    if method not in ("floyd_steinberg", "atkinson"):
        raise ValueError("Invalid dither method")
    settings = load_settings()
    settings["default_dither_method"] = method
    save_settings(settings)


def record_driver_fetch() -> None:
    """Record when the ESP32 driver last fetched latest_frame.bin."""
    settings = load_settings()
    settings["last_driver_fetch_at"] = datetime.now(timezone.utc).isoformat()
    save_settings(settings)


def format_next_driver_wake() -> str:
    """Countdown to the next scheduled ESP32 timer wake (firmware interval)."""
    last_fetch_at = load_settings().get("last_driver_fetch_at")
    interval = DRIVER_WAKE_INTERVAL_SECONDS

    if not last_fetch_at:
        return "Next driver wake: unknown (not fetched yet)"

    try:
        last = datetime.fromisoformat(last_fetch_at)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        next_at = last.timestamp() + interval
        remaining = int(next_at - datetime.now(timezone.utc).timestamp())
    except (TypeError, ValueError):
        return "Next driver wake: unknown"

    if remaining <= 0:
        return "Next driver wake: due now"
    hours, rem = divmod(remaining, 3600)
    minutes = rem // 60
    if hours:
        return f"Next driver wake: in {hours}h {minutes}m"
    return f"Next driver wake: in {minutes}m"

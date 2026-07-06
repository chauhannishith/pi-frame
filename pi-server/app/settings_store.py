"""Runtime settings persisted alongside library state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import DATA_DIR, DITHER_METHOD, PROCESSING_INTERVAL_SECONDS

SETTINGS_PATH = Path(DATA_DIR) / "settings.json"


def _default_settings() -> dict:
    return {
        "processing_interval_seconds": PROCESSING_INTERVAL_SECONDS,
        "default_dither_method": DITHER_METHOD,
    }


def load_settings() -> dict:
    if not SETTINGS_PATH.is_file():
        return _default_settings()
    data = json.loads(SETTINGS_PATH.read_text())
    base = _default_settings()
    base.update({k: v for k, v in data.items() if k in base})
    return base


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


def get_processing_interval_seconds() -> int:
    return int(load_settings()["processing_interval_seconds"])


def set_processing_interval_seconds(seconds: int) -> None:
    if seconds < 300:
        raise ValueError("Interval must be at least 5 minutes")
    settings = load_settings()
    settings["processing_interval_seconds"] = int(seconds)
    save_settings(settings)


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


def interval_preset_options() -> list[tuple[str, int, str]]:
    return [
        ("1h", 3600, "Every hour"),
        ("6h", 21600, "Every 6 hours"),
        ("12h", 43200, "Every 12 hours"),
        ("24h", 86400, "Every 24 hours"),
        ("48h", 172800, "Every 48 hours"),
    ]


def format_next_rotation(last_processed_at: str | None, interval_seconds: int) -> str:
    if not last_processed_at:
        return "Next auto-rotate: after first image is processed"
    try:
        last = datetime.fromisoformat(last_processed_at)
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        next_at = last.timestamp() + interval_seconds
        remaining = int(next_at - datetime.now(timezone.utc).timestamp())
    except (TypeError, ValueError):
        return "Next auto-rotate: unknown"

    if remaining <= 0:
        return "Next auto-rotate: due now"
    hours, rem = divmod(remaining, 3600)
    minutes = rem // 60
    if hours:
        return f"Next auto-rotate: in {hours}h {minutes}m"
    return f"Next auto-rotate: in {minutes}m"

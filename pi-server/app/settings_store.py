"""Runtime settings persisted alongside library state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from config import DATA_DIR, DITHER_METHOD

SETTINGS_PATH = Path(DATA_DIR) / "settings.json"

_SETTING_KEYS = (
    "default_dither_method",
    "frame_orientation",
    "last_preview_source",
    "last_preview_dither",
    "last_preview_at",
)


def _default_settings() -> dict:
    return {
        "default_dither_method": DITHER_METHOD,
        "frame_orientation": "landscape",
        "last_preview_source": None,
        "last_preview_dither": None,
        "last_preview_at": None,
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


def set_default_dither_method(method: str) -> None:
    method = method.lower()
    if method not in ("floyd_steinberg", "atkinson"):
        raise ValueError("Invalid dither method")
    settings = load_settings()
    settings["default_dither_method"] = method
    save_settings(settings)


def get_frame_orientation() -> str:
    from processing.frame_orientation import normalize_orientation

    return normalize_orientation(load_settings().get("frame_orientation"))


def set_frame_orientation(orientation: str) -> None:
    from processing.frame_orientation import normalize_orientation

    orientation = normalize_orientation(orientation)
    settings = load_settings()
    settings["frame_orientation"] = orientation
    save_settings(settings)


def record_preview(
    source_name: str,
    dither_method: str,
    frame_orientation: str | None = None,
) -> None:
    """Record which image and dither method produced the current preview.png."""
    from processing.frame_orientation import normalize_orientation

    settings = load_settings()
    settings["last_preview_source"] = source_name
    settings["last_preview_dither"] = dither_method
    settings["last_preview_at"] = datetime.now(timezone.utc).isoformat()
    if frame_orientation is not None:
        settings["frame_orientation"] = normalize_orientation(frame_orientation)
    save_settings(settings)


def _format_relative_time(iso: str | None) -> str:
    if not iso:
        return "unknown"
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        seconds = int(datetime.now(timezone.utc).timestamp() - dt.timestamp())
    except (TypeError, ValueError):
        return "unknown"

    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h {minutes % 60}m ago"
    days = hours // 24
    return f"{days}d ago"


def format_frame_output_status(
    on_frame_source: str | None,
    last_processed_at: str | None,
) -> tuple[str, str, str]:
    """
    Return (status_label, filename, relative_time) for the sidebar frame output section.

    status_label is either "Ready to push" or "On frame".
    """
    settings = load_settings()
    preview_source = settings.get("last_preview_source")
    preview_at = settings.get("last_preview_at")

    if preview_source:
        on_frame = on_frame_source is not None and preview_source == on_frame_source
        status = "On frame" if on_frame else "Ready to push"
        time_at = preview_at or last_processed_at
        return status, preview_source, _format_relative_time(time_at)

    if on_frame_source:
        return "On frame", on_frame_source, _format_relative_time(last_processed_at)

    return "No preview yet", "—", "—"

"""
Image library management — drive-like storage with daily rotation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from config import GALLERY_UPLOAD_EXTENSIONS, LIBRARY_STATE_PATH, SUPPORTED_IMAGE_EXTENSIONS
from thumbnails import delete_thumbnail
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)


def _state_path(state_path: str | Path | None = None) -> Path:
    return Path(state_path or LIBRARY_STATE_PATH)


def _load_state(state_path: str | Path | None = None) -> dict:
    path = _state_path(state_path)
    if not path.is_file():
        return {"current_index": 0, "last_source": None, "last_processed_at": None}
    return json.loads(path.read_text())


def _save_state(state: dict, state_path: str | Path | None = None) -> None:
    path = _state_path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def list_library_images(source_dir: str | Path) -> list[Path]:
    """Return supported images in the library, sorted by filename."""
    directory = Path(source_dir)
    if not directory.is_dir():
        return []
    return sorted(
        (
            p
            for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
        ),
        key=lambda p: p.name.lower(),
    )


def safe_library_filename(filename: str) -> str | None:
    """Sanitize and validate a library filename."""
    clean = secure_filename(filename)
    if not clean or Path(clean).suffix.lower() not in GALLERY_UPLOAD_EXTENSIONS:
        return None
    return clean


def resolve_library_file(source_dir: str | Path, filename: str) -> Path | None:
    """Resolve a filename within the library, rejecting path traversal."""
    clean = safe_library_filename(filename)
    if clean is None:
        return None
    path = Path(source_dir) / clean
    if not path.is_file():
        return None
    return path


def add_to_library(
    source_dir: str | Path,
    file_storage,
    original_filename: str,
) -> Path:
    """Save an uploaded file into the image library."""
    clean = safe_library_filename(original_filename)
    if clean is None:
        raise ValueError("Unsupported file type")

    directory = Path(source_dir)
    directory.mkdir(parents=True, exist_ok=True)

    dest = directory / clean
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        counter = 1
        while dest.exists():
            dest = directory / f"{stem}_{counter}{suffix}"
            counter += 1

    file_storage.save(dest)
    logger.info("Added to library: %s", dest.name)
    return dest


def delete_from_library(
    source_dir: str | Path,
    filename: str,
    state_path: str | Path | None = None,
) -> bool:
    """Delete an image from the library."""
    deleted, _failed = delete_many_from_library(source_dir, [filename], state_path=state_path)
    return deleted == 1


def delete_many_from_library(
    source_dir: str | Path,
    filenames: list[str],
    state_path: str | Path | None = None,
) -> tuple[int, list[str]]:
    """Delete multiple library images. Returns (deleted_count, filenames_not_found)."""
    deleted_names: list[str] = []
    failed: list[str] = []

    for filename in filenames:
        path = resolve_library_file(source_dir, filename)
        if path is None:
            failed.append(filename)
            continue
        path.unlink()
        logger.info("Deleted from library: %s", path.name)
        delete_thumbnail(path)
        deleted_names.append(path.name)

    if not deleted_names:
        return 0, failed

    images = list_library_images(source_dir)
    remaining = {p.name for p in images}
    state = _load_state(state_path)
    if not images:
        state["current_index"] = 0
        state["last_source"] = None
    else:
        if state.get("last_source") not in remaining:
            state["last_source"] = None
        if state["current_index"] >= len(images):
            state["current_index"] = 0
    _save_state(state, state_path)
    return len(deleted_names), failed


def next_image_for_processing(
    source_dir: str | Path,
    state_path: str | Path | None = None,
) -> Path | None:
    """
    Pick the next image in rotation, advance the index, and return it.

    Used by the daily job and the CHANGE button.
    """
    images = list_library_images(source_dir)
    if not images:
        return None

    state = _load_state(state_path)
    idx = state["current_index"] % len(images)
    chosen = images[idx]
    state["current_index"] = (idx + 1) % len(images)
    state["last_source"] = chosen.name
    state["last_processed_at"] = datetime.now(timezone.utc).isoformat()
    _save_state(state, state_path)
    logger.info("Selected library image [%d/%d]: %s", idx, len(images), chosen.name)
    return chosen


def get_library_status(source_dir: str | Path, state_path: str | Path | None = None) -> dict:
    """Summary for the gallery UI."""
    images = list_library_images(source_dir)
    state = _load_state(state_path)
    return {
        "count": len(images),
        "next_index": state["current_index"] % len(images) if images else 0,
        "last_source": state.get("last_source"),
        "last_processed_at": state.get("last_processed_at"),
        "images": [{"name": p.name, "size_kb": round(p.stat().st_size / 1024)} for p in images],
    }


def record_processed_source(source_name: str, state_path: str | Path | None = None) -> None:
    """Record which image was last processed (without advancing rotation)."""
    state = _load_state(state_path)
    state["last_source"] = source_name
    state["last_processed_at"] = datetime.now(timezone.utc).isoformat()
    _save_state(state, state_path)

"""Shared frame processing with thread-safe locking."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from config import (
    FRAME_HEIGHT,
    FRAME_WIDTH,
    LATEST_FRAME_PATH,
    PREVIEW_PATH,
    SOURCE_IMAGES_DIR,
)
from library import record_processed_source, resolve_library_file
from processing.pipeline import process_image_to_binary, run_library_processing
from settings_store import (
    get_active_dither_method,
    get_default_dither_method,
    get_frame_orientation,
    load_settings,
    record_preview,
    set_default_dither_method,
    set_frame_orientation,
)

logger = logging.getLogger(__name__)

processing_lock = threading.Lock()


def _orientation() -> str:
    return get_frame_orientation()


def format_quick_action_message(changed: str, source: str | None) -> str:
    if source:
        return (
            f"Updated frame output ({changed}) for {source}. "
            "Press the wake button to refresh the display."
        )
    return changed


def reprocess_active_output(
    *,
    dither_method: str | None = None,
    frame_orientation: str | None = None,
) -> str | None:
    """Reprocess the last active image to latest_frame.bin."""
    preview_source = load_settings().get("last_preview_source")
    if not preview_source:
        return None

    path = resolve_library_file(SOURCE_IMAGES_DIR, preview_source)
    if path is None:
        return None

    process_specific_image(path, dither_method=dither_method, frame_orientation=frame_orientation)
    return preview_source


def change_frame(dither_method: str | None = None) -> str | None:
    """
    Advance library rotation and process the next image.

    Returns the processed source filename, or None if library is empty.
    """
    method = dither_method or get_default_dither_method()
    orientation = _orientation()
    with processing_lock:
        result = run_library_processing(
            SOURCE_IMAGES_DIR,
            LATEST_FRAME_PATH,
            width=FRAME_WIDTH,
            height=FRAME_HEIGHT,
            preview_path=PREVIEW_PATH,
            dither_method=method,
            frame_orientation=orientation,
        )
    if result is None:
        return None
    record_preview(result.name, method, orientation)
    logger.info("Frame changed to %s", result.name)
    return result.name


def toggle_frame_orientation() -> tuple[str, str | None]:
    """Toggle orientation and update frame output when an active source exists."""
    current = get_frame_orientation()
    new = "portrait" if current == "landscape" else "landscape"
    set_frame_orientation(new)
    source = reprocess_active_output(frame_orientation=new)
    return new, source


def toggle_frame_dither() -> tuple[str, str | None]:
    """Toggle dither method and update frame output when an active source exists."""
    current = get_active_dither_method()
    new = "atkinson" if current == "floyd_steinberg" else "floyd_steinberg"
    set_default_dither_method(new)
    source = reprocess_active_output(dither_method=new)
    return new, source


def generate_preview(
    source: str | Path,
    dither_method: str | None = None,
    frame_orientation: str | None = None,
) -> str:
    """Dither an image and write preview PNG only — does not update the frame binary."""
    method = dither_method or get_default_dither_method()
    orientation = frame_orientation or _orientation()
    source_path = Path(source)
    with processing_lock:
        process_image_to_binary(
            source_path,
            output=None,
            width=FRAME_WIDTH,
            height=FRAME_HEIGHT,
            preview_path=PREVIEW_PATH,
            dither_method=method,
            frame_orientation=orientation,
        )
    record_preview(source_path.name, method, orientation)
    logger.info("Generated preview for: %s (%s)", source_path.name, orientation)
    return source_path.name


def process_specific_image(
    source: str | Path,
    dither_method: str | None = None,
    frame_orientation: str | None = None,
) -> str:
    """Process a specific library image without advancing rotation."""
    method = dither_method or get_default_dither_method()
    orientation = frame_orientation or _orientation()
    source_path = Path(source)
    with processing_lock:
        process_image_to_binary(
            source_path,
            LATEST_FRAME_PATH,
            width=FRAME_WIDTH,
            height=FRAME_HEIGHT,
            preview_path=PREVIEW_PATH,
            dither_method=method,
            frame_orientation=orientation,
        )
        record_processed_source(source_path.name)
    record_preview(source_path.name, method, orientation)
    logger.info("Processed specific image: %s (%s)", source_path.name, orientation)
    return source_path.name

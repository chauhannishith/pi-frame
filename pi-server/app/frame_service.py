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
from library import record_processed_source
from processing.pipeline import process_image_to_binary, run_library_processing
from settings_store import get_default_dither_method, record_preview

logger = logging.getLogger(__name__)

processing_lock = threading.Lock()


def change_frame(dither_method: str | None = None) -> str | None:
    """
    Advance library rotation and process the next image.

    Returns the processed source filename, or None if library is empty.
    """
    method = dither_method or get_default_dither_method()
    with processing_lock:
        result = run_library_processing(
            SOURCE_IMAGES_DIR,
            LATEST_FRAME_PATH,
            width=FRAME_WIDTH,
            height=FRAME_HEIGHT,
            preview_path=PREVIEW_PATH,
            dither_method=method,
        )
    if result is None:
        return None
    record_preview(result.name, method)
    logger.info("Frame changed to %s", result.name)
    return result.name


def generate_preview(
    source: str | Path,
    dither_method: str | None = None,
) -> str:
    """Dither an image and write preview PNG only — does not update the frame binary."""
    method = dither_method or get_default_dither_method()
    source_path = Path(source)
    with processing_lock:
        process_image_to_binary(
            source_path,
            output=None,
            width=FRAME_WIDTH,
            height=FRAME_HEIGHT,
            preview_path=PREVIEW_PATH,
            dither_method=method,
        )
    record_preview(source_path.name, method)
    logger.info("Generated preview for: %s", source_path.name)
    return source_path.name


def process_specific_image(
    source: str | Path,
    dither_method: str | None = None,
) -> str:
    """Process a specific library image without advancing rotation."""
    method = dither_method or get_default_dither_method()
    source_path = Path(source)
    with processing_lock:
        process_image_to_binary(
            source_path,
            LATEST_FRAME_PATH,
            width=FRAME_WIDTH,
            height=FRAME_HEIGHT,
            preview_path=PREVIEW_PATH,
            dither_method=method,
        )
        record_processed_source(source_path.name)
    record_preview(source_path.name, method)
    logger.info("Processed specific image: %s", source_path.name)
    return source_path.name

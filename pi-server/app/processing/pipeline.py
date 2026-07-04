"""End-to-end pipeline: load, resize, quantize, and write frame binary."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from config import BINARY_PACK_MODE, DITHER_METHOD, FRAME_HEIGHT, FRAME_WIDTH
from processing.binary import pack_frame_buffer
from processing.dither import quantize_to_palette
from processing.resize import resize_for_display
from processing.sources import find_latest_source_image
from processing.types import DitherMethod, PackMode, ResizeMode

logger = logging.getLogger(__name__)


def process_image_to_binary(
    source: str | Path,
    output: str | Path,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
    *,
    resize_mode: ResizeMode | str = ResizeMode.COVER,
    dither_method: DitherMethod | str = DITHER_METHOD,
    pack_mode: PackMode | str = BINARY_PACK_MODE,
    palette_rgb=None,
) -> Path:
    """
    Full pipeline: load → resize → quantize → write raw binary frame buffer.

    Returns the output path.
    """
    source_path = Path(source)
    output_path = Path(output)

    if not source_path.is_file():
        raise FileNotFoundError(f"Source image not found: {source_path}")

    logger.info(
        "Processing %s -> %s (%dx%d, dither=%s, pack=%s)",
        source_path,
        output_path,
        width,
        height,
        dither_method,
        pack_mode,
    )

    with Image.open(source_path) as img:
        resized = resize_for_display(img, width, height, mode=resize_mode)

    indices = quantize_to_palette(
        resized,
        palette_rgb=palette_rgb,
        method=dither_method,
    )

    frame_bytes = pack_frame_buffer(indices, mode=pack_mode)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(frame_bytes)

    logger.info("Wrote %d bytes to %s", len(frame_bytes), output_path)
    return output_path


def run_daily_processing(
    source_dir: str | Path,
    output_path: str | Path,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
) -> None:
    """Process the newest source image and write the frame binary."""
    source = find_latest_source_image(source_dir)
    if source is None:
        logger.warning("No source images found in %s", source_dir)
        return

    process_image_to_binary(source, output_path, width=width, height=height)

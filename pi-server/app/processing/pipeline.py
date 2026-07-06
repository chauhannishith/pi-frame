"""End-to-end pipeline: load, resize, quantize, and write frame binary."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageOps

from config import BINARY_PACK_MODE, DITHER_METHOD, FRAME_HEIGHT, FRAME_WIDTH, PREVIEW_PATH
from library import next_image_for_processing
from palette import EINK_PALETTE_RGB
from processing.binary import pack_frame_buffer
from processing.dither import (
    composite_indices_on_frame,
    indices_to_preview_rgb,
    palette_index_for_rgb,
    quantize_to_palette,
)
from processing.resize import resize_for_display
from processing.types import DitherMethod, PackMode, ResizeMode

logger = logging.getLogger(__name__)


def process_image_to_binary(
    source: str | Path,
    output: str | Path | None,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
    *,
    preview_path: str | Path | None = None,
    resize_mode: ResizeMode | str = ResizeMode.COVER,
    dither_method: DitherMethod | str = DITHER_METHOD,
    pack_mode: PackMode | str = BINARY_PACK_MODE,
    palette_rgb=None,
) -> Path | None:
    """
    Full pipeline: load → resize → quantize → write raw binary frame buffer.

    When output is None, skips writing the binary (preview-only mode).
    Optionally writes an RGB preview PNG showing the dithered result.
    Returns the binary output path, or None when output was skipped.
    """
    source_path = Path(source)
    output_path = Path(output) if output is not None else None

    if not source_path.is_file():
        raise FileNotFoundError(f"Source image not found: {source_path}")

    logger.info(
        "Processing %s -> %s (%dx%d, dither=%s, pack=%s)",
        source_path,
        output_path or "(preview only)",
        width,
        height,
        dither_method,
        pack_mode,
    )

    with Image.open(source_path) as img:
        img = ImageOps.exif_transpose(img)
        layout = resize_for_display(img, width, height, mode=resize_mode)

    palette = palette_rgb if palette_rgb is not None else EINK_PALETTE_RGB
    content_indices = quantize_to_palette(
        layout.content,
        palette_rgb=palette,
        method=dither_method,
    )
    pad_index = palette_index_for_rgb(layout.pad_color, palette)
    paste_x, paste_y = layout.paste_xy
    frame_w, frame_h = layout.frame_size
    indices = composite_indices_on_frame(
        content_indices,
        frame_w,
        frame_h,
        paste_x,
        paste_y,
        pad_index,
    )

    frame_bytes = pack_frame_buffer(indices, mode=pack_mode)
    output_path = Path(output) if output is not None else None
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(frame_bytes)
        logger.info("Wrote %d bytes to %s", len(frame_bytes), output_path)

    if preview_path is not None:
        preview_file = Path(preview_path)
        preview_rgb = indices_to_preview_rgb(indices, palette_rgb)
        Image.fromarray(preview_rgb, mode="RGB").save(preview_file)
        logger.info("Wrote preview to %s", preview_file)

    return output_path


def run_library_processing(
    source_dir: str | Path,
    output_path: str | Path,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
    *,
    preview_path: str | Path | None = PREVIEW_PATH,
    dither_method: DitherMethod | str = DITHER_METHOD,
) -> Path | None:
    """
    Advance the library rotation, process the next image, and write outputs.

    Returns the source path, or None if the library is empty.
    """
    source = next_image_for_processing(source_dir)
    if source is None:
        logger.warning("No source images in library at %s", source_dir)
        return None

    process_image_to_binary(
        source,
        output_path,
        width=width,
        height=height,
        preview_path=preview_path,
        dither_method=dither_method,
    )
    return source

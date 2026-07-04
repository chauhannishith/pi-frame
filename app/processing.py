"""
Daily image processing pipeline for the 6-color e-ink frame.

Drop your dithering logic into `process_images` — e.g. Atkinson or
Floyd-Steinberg quantization into the frame's 6-color palette.
"""

import logging
from pathlib import Path

from config import FRAME_HEIGHT, FRAME_WIDTH, LATEST_FRAME_PATH, SOURCE_IMAGES_DIR

logger = logging.getLogger(__name__)


def process_images() -> None:
    """
    Main processing entry point. Called once per daily cycle.

    Expected workflow (implement when ready):
      1. Load source images from SOURCE_IMAGES_DIR
      2. Resize / crop to FRAME_WIDTH x FRAME_HEIGHT
      3. Apply 6-color dithering (Atkinson, Floyd-Steinberg, etc.)
      4. Pack pixels into a binary frame buffer
      5. Write result to LATEST_FRAME_PATH
    """
    source_dir = Path(SOURCE_IMAGES_DIR)
    output_path = Path(LATEST_FRAME_PATH)

    logger.info(
        "Processing placeholder — source=%s output=%s frame=%dx%d",
        source_dir,
        output_path,
        FRAME_WIDTH,
        FRAME_HEIGHT,
    )

    # TODO: implement dithering pipeline here
    #
    # from PIL import Image
    # import numpy as np
    #
    # image = load_and_compose(source_dir)
    # dithered = apply_six_color_dither(image)
    # write_frame_binary(dithered, output_path)


def run_daily_processing() -> None:
    """Wrapper with error handling for the background thread."""
    try:
        process_images()
        logger.info("Daily processing cycle completed")
    except Exception:
        logger.exception("Daily processing cycle failed")

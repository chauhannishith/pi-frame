"""
Flask server for the 7.3-inch 6-color e-ink frame.

Serves the latest processed frame binary over HTTP and runs a background
thread that triggers daily image processing (dithering pipeline TBD).
"""

import logging
import os
import threading
import time
from pathlib import Path

from flask import Flask, abort, send_file

# ---------------------------------------------------------------------------
# Configuration — override via environment variables in docker-compose.yml
# ---------------------------------------------------------------------------

LATEST_FRAME_PATH = os.environ.get("LATEST_FRAME_PATH", "/app/latest_frame.bin")
SOURCE_IMAGES_DIR = os.environ.get("SOURCE_IMAGES_DIR", "/app/source_images")

FRAME_WIDTH = int(os.environ.get("FRAME_WIDTH", "800"))
FRAME_HEIGHT = int(os.environ.get("FRAME_HEIGHT", "480"))

PROCESSING_INTERVAL_SECONDS = int(
    os.environ.get("PROCESSING_INTERVAL_SECONDS", str(24 * 60 * 60))
)

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Image processing placeholder — drop your dithering logic here
# ---------------------------------------------------------------------------


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


def processing_loop() -> None:
    """Background loop — runs processing once, then sleeps 24 hours."""
    while True:
        run_daily_processing()
        logger.info(
            "Next processing cycle in %d seconds (%.1f hours)",
            PROCESSING_INTERVAL_SECONDS,
            PROCESSING_INTERVAL_SECONDS / 3600,
        )
        time.sleep(PROCESSING_INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------


@app.route("/get_latest_frame.bin", methods=["GET"])
def get_latest_frame():
    """Serve the latest processed frame as a binary download."""
    if not os.path.isfile(LATEST_FRAME_PATH):
        logger.warning("Frame file not found: %s", LATEST_FRAME_PATH)
        abort(404, description="No frame available yet")

    return send_file(
        LATEST_FRAME_PATH,
        mimetype="application/octet-stream",
        download_name="latest_frame.bin",
    )


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


def start_background_processing() -> threading.Thread:
    thread = threading.Thread(
        target=processing_loop,
        name="daily-processing",
        daemon=True,
    )
    thread.start()
    logger.info("Background processing thread started")
    return thread


if __name__ == "__main__":
    start_background_processing()
    logger.info("Starting Flask server on %s:%d", FLASK_HOST, FLASK_PORT)
    app.run(host=FLASK_HOST, port=FLASK_PORT)

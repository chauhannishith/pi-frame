"""
Flask server for the 7.3-inch 6-color e-ink frame.

Serves the latest processed frame binary and runs a background thread
that triggers daily image processing.
"""

import logging
import os
import threading
import time

from flask import Flask, abort, send_file

from config import (
    FLASK_HOST,
    FLASK_PORT,
    LATEST_FRAME_PATH,
    PROCESSING_INTERVAL_SECONDS,
)
from processing import run_daily_processing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


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

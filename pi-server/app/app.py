"""
Flask server for the 7.3-inch 6-color e-ink frame.

Serves the latest processed frame binary over HTTP and runs a background
thread that triggers daily image processing.
"""

import logging
import os
import threading
import time

from flask import Flask, abort, redirect, send_file, url_for
from gallery_routes import gallery_bp
from google_routes import google_bp
from settings_routes import settings_bp

from config import (
    FLASK_HOST,
    FLASK_PORT,
    FLASK_SECRET_KEY,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    LATEST_FRAME_PATH,
    PREVIEW_PATH,
    SOURCE_IMAGES_DIR,
)
from frame_service import processing_lock
from processing.pipeline import run_library_processing
from settings_store import get_default_dither_method, get_processing_interval_seconds

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024  # 64 MB total upload limit

app.register_blueprint(gallery_bp)
app.register_blueprint(google_bp)
app.register_blueprint(settings_bp)


def run_daily_processing() -> None:
    """Advance library rotation and process the next image."""
    try:
        with processing_lock:
            run_library_processing(
                SOURCE_IMAGES_DIR,
                LATEST_FRAME_PATH,
                width=FRAME_WIDTH,
                height=FRAME_HEIGHT,
                preview_path=PREVIEW_PATH,
                dither_method=get_default_dither_method(),
            )
        logger.info("Daily processing cycle completed")
    except Exception:
        logger.exception("Daily processing cycle failed")


def processing_loop() -> None:
    while True:
        run_daily_processing()
        interval = get_processing_interval_seconds()
        logger.info(
            "Next processing cycle in %d seconds (%.1f hours)",
            interval,
            interval / 3600,
        )
        time.sleep(interval)


@app.route("/")
def index():
    return redirect("/gallery")


@app.route("/upload")
@app.route("/preview")
def legacy_routes():
    """Removed — preview and push live on gallery image pages."""
    return redirect(url_for("gallery.gallery_index"))


@app.route("/preview.png", methods=["GET"])
def preview_image():
    if not os.path.isfile(PREVIEW_PATH):
        abort(404)
    return send_file(PREVIEW_PATH, mimetype="image/png")


@app.route("/get_latest_frame.bin", methods=["GET"])
def get_latest_frame():
    if not os.path.isfile(LATEST_FRAME_PATH):
        abort(404, description="No frame available yet")
    return send_file(
        LATEST_FRAME_PATH,
        mimetype="application/octet-stream",
        download_name="latest_frame.bin",
    )


def start_background_processing() -> threading.Thread:
    thread = threading.Thread(target=processing_loop, name="daily-processing", daemon=True)
    thread.start()
    logger.info("Background processing thread started")
    return thread


if __name__ == "__main__":
    start_background_processing()
    logger.info("Starting Flask server on %s:%d", FLASK_HOST, FLASK_PORT)
    app.run(host=FLASK_HOST, port=FLASK_PORT)

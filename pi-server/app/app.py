"""
Flask server for the 7.3-inch 6-color e-ink frame.

Serves the latest processed frame binary over HTTP for the ESP32 driver.
"""

import logging
import os

from flask import Flask, abort, redirect, send_file, url_for
from gallery_routes import gallery_bp
from google_routes import google_bp
from settings_routes import settings_bp

from config import (
    FLASK_HOST,
    FLASK_PORT,
    FLASK_SECRET_KEY,
    LATEST_FRAME_PATH,
    PREVIEW_PATH,
)

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


if __name__ == "__main__":
    logger.info("Starting Flask server on %s:%d", FLASK_HOST, FLASK_PORT)
    app.run(host=FLASK_HOST, port=FLASK_PORT)

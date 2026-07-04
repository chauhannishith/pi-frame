"""
Flask server for the 7.3-inch 6-color e-ink frame.

Serves the latest processed frame binary over HTTP and runs a background
thread that triggers daily image processing.
"""

import logging
import os
import threading
import time
import uuid
from pathlib import Path

from flask import Flask, abort, redirect, request, send_file
from werkzeug.utils import secure_filename

from config import (
    FLASK_HOST,
    FLASK_PORT,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    LATEST_FRAME_PATH,
    PREVIEW_PATH,
    PROCESSING_INTERVAL_SECONDS,
    SOURCE_IMAGES_DIR,
    UPLOAD_TEMP_DIR,
)
from processing import process_image_to_binary, run_daily_processing as execute_daily_processing

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload limit

# Prevents manual uploads and the background thread from writing outputs at once
processing_lock = threading.Lock()

UPLOAD_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

UPLOAD_FORM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>pi-frame upload</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: system-ui, sans-serif;
      max-width: 420px;
      margin: 3rem auto;
      padding: 0 1rem;
      color: #222;
    }
    h1 { font-size: 1.25rem; margin-bottom: 0.25rem; }
    p { color: #555; font-size: 0.9rem; margin-top: 0; }
    form {
      margin-top: 1.5rem;
      padding: 1.25rem;
      border: 1px solid #ddd;
      border-radius: 8px;
      background: #fafafa;
    }
    input[type="file"] { display: block; width: 100%; margin-bottom: 1rem; }
    button {
      background: #222;
      color: #fff;
      border: none;
      padding: 0.6rem 1.2rem;
      border-radius: 6px;
      cursor: pointer;
      font-size: 0.95rem;
    }
    button:hover { background: #444; }
    .error {
      margin-top: 1rem;
      padding: 0.75rem 1rem;
      background: #fee;
      border: 1px solid #fcc;
      border-radius: 6px;
      color: #900;
      font-size: 0.9rem;
    }
  </style>
</head>
<body>
  <h1>Manual image upload</h1>
  <p>Upload a JPG or PNG to preview 6-color dithering at 800×480.</p>
  <form method="post" enctype="multipart/form-data">
    <input type="file" name="image" accept=".jpg,.jpeg,.png,image/jpeg,image/png" required>
    <button type="submit">Process &amp; preview</button>
  </form>
  {error_block}
</body>
</html>"""


def _render_upload_form(error: str | None = None) -> str:
    error_block = f'<div class="error">{error}</div>' if error else ""
    return UPLOAD_FORM_HTML.replace("{error_block}", error_block)


def _allowed_upload(filename: str) -> bool:
    return Path(filename).suffix.lower() in UPLOAD_ALLOWED_EXTENSIONS


def run_daily_processing() -> None:
    """Wrapper with error handling for the background thread."""
    try:
        with processing_lock:
            execute_daily_processing(
                SOURCE_IMAGES_DIR,
                LATEST_FRAME_PATH,
                width=FRAME_WIDTH,
                height=FRAME_HEIGHT,
                preview_path=PREVIEW_PATH,
            )
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


@app.route("/upload", methods=["GET", "POST"])
def upload():
    """Manual upload form and processing entry point."""
    if request.method == "GET":
        return _render_upload_form()

    uploaded = request.files.get("image")
    if uploaded is None or not uploaded.filename:
        return _render_upload_form("No file selected.")

    filename = secure_filename(uploaded.filename)
    if not filename or not _allowed_upload(filename):
        return _render_upload_form("Only JPG and PNG files are supported.")

    temp_dir = Path(UPLOAD_TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4().hex}{Path(filename).suffix.lower()}"

    try:
        uploaded.save(temp_path)
        logger.info("Manual upload saved to %s", temp_path)

        with processing_lock:
            process_image_to_binary(
                temp_path,
                LATEST_FRAME_PATH,
                width=FRAME_WIDTH,
                height=FRAME_HEIGHT,
                preview_path=PREVIEW_PATH,
            )

        logger.info("Manual upload processed — redirecting to preview")
        return redirect("/preview", code=303)

    except Exception:
        logger.exception("Manual upload processing failed")
        return _render_upload_form("Processing failed. Check server logs for details.")

    finally:
        temp_path.unlink(missing_ok=True)


@app.route("/preview", methods=["GET"])
def preview():
    """Serve the dithered RGB preview image for browser inspection."""
    if not os.path.isfile(PREVIEW_PATH):
        abort(404, description="No preview available yet — upload an image first")

    return send_file(PREVIEW_PATH, mimetype="image/png")


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

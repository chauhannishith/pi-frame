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

from flask import Flask, abort, redirect, request, send_file, url_for
from gallery_routes import gallery_bp
from google_routes import google_bp
from werkzeug.utils import secure_filename

from config import (
    FLASK_HOST,
    FLASK_PORT,
    FLASK_SECRET_KEY,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    LATEST_FRAME_PATH,
    PREVIEW_PATH,
    PROCESSING_INTERVAL_SECONDS,
    SOURCE_IMAGES_DIR,
    UPLOAD_TEMP_DIR,
)
from frame_service import processing_lock
from library import resolve_library_file
from preview_views import DITHER_OPTIONS, render_image_view_page
from processing import process_image_to_binary
from processing.pipeline import run_library_processing
from user_errors import format_user_error

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

UPLOAD_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

UPLOAD_FORM_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>pi-frame upload</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; max-width: 420px; margin: 3rem auto; padding: 0 1rem; color: #222; }
    nav { margin-bottom: 1rem; font-size: 0.9rem; }
    nav a { margin-right: 1rem; }
    h1 { font-size: 1.25rem; margin-bottom: 0.25rem; }
    p { color: #555; font-size: 0.9rem; margin-top: 0; }
    form { margin-top: 1.5rem; padding: 1.25rem; border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }
    label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.35rem; color: #444; }
    input[type="file"], select { display: block; width: 100%; margin-bottom: 1rem; font-size: 0.95rem; }
    select { padding: 0.45rem; border-radius: 6px; border: 1px solid #ccc; }
    button { background: #222; color: #fff; border: none; padding: 0.6rem 1.2rem; border-radius: 6px; cursor: pointer; font-size: 0.95rem; }
    button:hover { background: #444; }
    .error { margin-top: 1rem; padding: 0.75rem 1rem; background: #fee; border: 1px solid #fcc; border-radius: 6px; color: #900; font-size: 0.9rem; }
  </style>
</head>
<body>
  <nav><a href="/gallery">Gallery</a><a href="/google">Google Photos</a><a href="/preview">Preview</a></nav>
  <h1>Quick test upload</h1>
  <p>One-off dither test — does not add to the library.</p>
  <form method="post" enctype="multipart/form-data">
    <label for="image">Image file</label>
    <input id="image" type="file" name="image" accept=".jpg,.jpeg,.png,image/jpeg,image/png" required>
    <label for="dither_method">Dithering method</label>
    <select id="dither_method" name="dither_method">
      <option value="floyd_steinberg"{fs_selected}>Floyd-Steinberg</option>
      <option value="atkinson"{atkinson_selected}>Atkinson</option>
    </select>
    <button type="submit">Process &amp; preview</button>
  </form>
  {error_block}
</body>
</html>"""


def _render_upload_form(error: str | None = None, dither_method: str = "floyd_steinberg") -> str:
    if dither_method not in DITHER_OPTIONS:
        dither_method = "floyd_steinberg"
    error_block = f'<div class="error">{error}</div>' if error else ""
    html = UPLOAD_FORM_HTML.replace("{error_block}", error_block)
    html = html.replace("{fs_selected}", ' selected' if dither_method == "floyd_steinberg" else "")
    html = html.replace("{atkinson_selected}", ' selected' if dither_method == "atkinson" else "")
    return html


def _allowed_upload(filename: str) -> bool:
    return Path(filename).suffix.lower() in UPLOAD_ALLOWED_EXTENSIONS


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
            )
        logger.info("Daily processing cycle completed")
    except Exception:
        logger.exception("Daily processing cycle failed")


def processing_loop() -> None:
    while True:
        run_daily_processing()
        logger.info(
            "Next processing cycle in %d seconds (%.1f hours)",
            PROCESSING_INTERVAL_SECONDS,
            PROCESSING_INTERVAL_SECONDS / 3600,
        )
        time.sleep(PROCESSING_INTERVAL_SECONDS)


@app.route("/")
def index():
    return redirect("/gallery")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        return _render_upload_form()

    uploaded = request.files.get("image")
    dither_method = request.form.get("dither_method", "floyd_steinberg")

    if uploaded is None or not uploaded.filename:
        return _render_upload_form("No file selected.", dither_method=dither_method)

    filename = secure_filename(uploaded.filename)
    if not filename or not _allowed_upload(filename):
        return _render_upload_form("Only JPG and PNG files are supported.", dither_method=dither_method)

    if dither_method not in DITHER_OPTIONS:
        return _render_upload_form("Invalid dithering method.", dither_method="floyd_steinberg")

    temp_dir = Path(UPLOAD_TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / f"{uuid.uuid4().hex}{Path(filename).suffix.lower()}"

    try:
        uploaded.save(temp_path)
        with processing_lock:
            process_image_to_binary(
                temp_path,
                LATEST_FRAME_PATH,
                width=FRAME_WIDTH,
                height=FRAME_HEIGHT,
                preview_path=PREVIEW_PATH,
                dither_method=dither_method,
            )
        return redirect(f"/preview?method={dither_method}&generated=1", code=303)
    except Exception as exc:
        logger.exception("Manual upload processing failed")
        return _render_upload_form(f"Processing failed: {format_user_error(exc)}", dither_method=dither_method)
    finally:
        temp_path.unlink(missing_ok=True)


@app.route("/preview", methods=["GET"])
def preview():
    """Show latest dithered preview, or redirect to gallery view for library images."""
    source = request.args.get("source")
    if source and resolve_library_file(SOURCE_IMAGES_DIR, source):
        return redirect(url_for(
            "gallery.gallery_view",
            filename=source,
            generated=request.args.get("generated", "1"),
            method=request.args.get("method", "default"),
        ))

    if request.args.get("generated") != "1" and not os.path.isfile(PREVIEW_PATH):
        abort(404, description="No preview available yet — generate one from the gallery")

    method = request.args.get("method", "floyd_steinberg")
    if method not in DITHER_OPTIONS:
        method = "floyd_steinberg"

    return render_image_view_page(
        source_name=source or "Latest preview",
        form_action="/upload",
        dither_method=method,
        show_dithered=os.path.isfile(PREVIEW_PATH),
        original_url=None,
        back_href="/upload",
        nav_active="preview",
        show_controls=False,
    )


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

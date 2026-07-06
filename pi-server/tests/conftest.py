import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))


@pytest.fixture
def solid_red_image() -> Image.Image:
    return Image.new("RGB", (100, 80), (255, 0, 0))


@pytest.fixture
def gradient_image() -> Image.Image:
    arr = np.zeros((60, 120, 3), dtype=np.uint8)
    for x in range(120):
        arr[:, x] = [x * 2, 64, 255 - x * 2]
    return Image.fromarray(arr, mode="RGB")


@pytest.fixture
def tiny_checker_image() -> Image.Image:
    img = Image.new("RGB", (4, 4))
    pixels = [
        (0, 0, 0), (255, 255, 255), (0, 0, 0), (255, 255, 255),
        (255, 255, 255), (0, 0, 0), (255, 255, 255), (0, 0, 0),
        (0, 0, 0), (255, 255, 255), (0, 0, 0), (255, 255, 255),
        (255, 255, 255), (0, 0, 0), (255, 255, 255), (0, 0, 0),
    ]
    img.putdata(pixels)
    return img


@pytest.fixture
def app_paths(tmp_path, monkeypatch):
    """Isolated data dirs and patched module-level path constants."""
    source_dir = tmp_path / "source_images"
    source_dir.mkdir()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    preview_path = tmp_path / "preview.png"
    frame_path = tmp_path / "latest_frame.bin"
    library_state = data_dir / "library_state.json"
    settings_path = data_dir / "settings.json"

    monkeypatch.setattr("config.SOURCE_IMAGES_DIR", str(source_dir))
    monkeypatch.setattr("config.DATA_DIR", str(data_dir))
    monkeypatch.setattr("config.PREVIEW_PATH", str(preview_path))
    monkeypatch.setattr("config.LATEST_FRAME_PATH", str(frame_path))
    monkeypatch.setattr("config.LIBRARY_STATE_PATH", str(library_state))

    monkeypatch.setattr("gallery_routes.SOURCE_IMAGES_DIR", str(source_dir))
    monkeypatch.setattr("frame_service.SOURCE_IMAGES_DIR", str(source_dir))
    monkeypatch.setattr("frame_service.PREVIEW_PATH", str(preview_path))
    monkeypatch.setattr("frame_service.LATEST_FRAME_PATH", str(frame_path))
    monkeypatch.setattr("library.LIBRARY_STATE_PATH", str(library_state))
    monkeypatch.setattr("settings_store.SETTINGS_PATH", settings_path)
    monkeypatch.setattr("thumbnails.DATA_DIR", str(data_dir))

    return {
        "source_dir": source_dir,
        "data_dir": data_dir,
        "preview_path": preview_path,
        "frame_path": frame_path,
        "library_state": library_state,
        "settings_path": settings_path,
    }


@pytest.fixture
def flask_client(app_paths):
    import os

    from flask import Flask, abort, redirect, send_file, url_for

    from gallery_routes import gallery_bp
    from settings_routes import settings_bp

    test_app = Flask(__name__)
    test_app.secret_key = "test"
    test_app.config["TESTING"] = True
    test_app.register_blueprint(gallery_bp)
    test_app.register_blueprint(settings_bp)

    preview_path = str(app_paths["preview_path"])
    frame_path = str(app_paths["frame_path"])

    @test_app.route("/")
    def index():
        return redirect("/gallery")

    @test_app.route("/upload")
    @test_app.route("/preview")
    def legacy_routes():
        return redirect(url_for("gallery.gallery_index"))

    @test_app.route("/preview.png")
    def preview_image():
        if not os.path.isfile(preview_path):
            abort(404)
        return send_file(preview_path, mimetype="image/png")

    @test_app.route("/get_latest_frame.bin")
    def get_latest_frame():
        if not os.path.isfile(frame_path):
            abort(404)
        return send_file(frame_path, mimetype="application/octet-stream")

    return test_app.test_client()


def seed_library_image(source_dir: Path, name: str = "photo.jpg", size: tuple[int, int] = (400, 300)) -> str:
    Image.new("RGB", size, (120, 80, 60)).save(source_dir / name, "JPEG")
    return name

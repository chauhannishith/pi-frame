import os

LATEST_FRAME_PATH = os.environ.get("LATEST_FRAME_PATH", "/app/latest_frame.bin")
SOURCE_IMAGES_DIR = os.environ.get("SOURCE_IMAGES_DIR", "/app/source_images")

FRAME_WIDTH = int(os.environ.get("FRAME_WIDTH", "800"))
FRAME_HEIGHT = int(os.environ.get("FRAME_HEIGHT", "480"))

PROCESSING_INTERVAL_SECONDS = int(
    os.environ.get("PROCESSING_INTERVAL_SECONDS", str(24 * 60 * 60))
)

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))

# Quantization: "floyd_steinberg" or "atkinson"
DITHER_METHOD = os.environ.get("DITHER_METHOD", "floyd_steinberg")

# Binary layout: "packed" (3-bit, 8 pixels / 3 bytes) or "byte" (1 index per byte)
BINARY_PACK_MODE = os.environ.get("BINARY_PACK_MODE", "byte")

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

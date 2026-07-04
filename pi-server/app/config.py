import os

LATEST_FRAME_PATH = os.environ.get("LATEST_FRAME_PATH", "/app/latest_frame.bin")
PREVIEW_PATH = os.environ.get("PREVIEW_PATH", "/app/preview.png")
SOURCE_IMAGES_DIR = os.environ.get("SOURCE_IMAGES_DIR", "/app/source_images")
UPLOAD_TEMP_DIR = os.environ.get("UPLOAD_TEMP_DIR", "/app/uploads")

FRAME_WIDTH = int(os.environ.get("FRAME_WIDTH", "800"))
FRAME_HEIGHT = int(os.environ.get("FRAME_HEIGHT", "480"))

PROCESSING_INTERVAL_SECONDS = int(
    os.environ.get("PROCESSING_INTERVAL_SECONDS", str(24 * 60 * 60))
)

FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))

# Quantization: "floyd_steinberg" or "atkinson"
DITHER_METHOD = os.environ.get("DITHER_METHOD", "floyd_steinberg")

# Floyd-Steinberg error damping (0.0–1.0) — reduces color bleed on skin tones
FLOYD_STEINBERG_ERROR_DAMPING = float(os.environ.get("FLOYD_STEINBERG_ERROR_DAMPING", "0.80"))

# Binary layout: "packed" (3-bit, 8 pixels / 3 bytes) or "byte" (1 index per byte)
BINARY_PACK_MODE = os.environ.get("BINARY_PACK_MODE", "byte")

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}

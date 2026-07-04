import os

# Paths
LATEST_FRAME_PATH = os.environ.get("LATEST_FRAME_PATH", "/app/latest_frame.bin")
SOURCE_IMAGES_DIR = os.environ.get("SOURCE_IMAGES_DIR", "/app/source_images")

# Display layout (6-color e-ink, 7.3-inch frame)
FRAME_WIDTH = int(os.environ.get("FRAME_WIDTH", "800"))
FRAME_HEIGHT = int(os.environ.get("FRAME_HEIGHT", "480"))

# Background processing interval (seconds)
PROCESSING_INTERVAL_SECONDS = int(
    os.environ.get("PROCESSING_INTERVAL_SECONDS", str(24 * 60 * 60))
)

# Flask
FLASK_HOST = os.environ.get("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.environ.get("FLASK_PORT", "5000"))

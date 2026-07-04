"""Source image discovery for the daily processing job."""

from pathlib import Path

from config import SUPPORTED_IMAGE_EXTENSIONS


def find_latest_source_image(source_dir: str | Path) -> Path | None:
    """Return the most recently modified supported image in source_dir."""
    directory = Path(source_dir)
    if not directory.is_dir():
        return None

    candidates = [
        p
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)

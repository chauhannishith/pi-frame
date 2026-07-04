"""Generate and cache small gallery thumbnails on disk."""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

from PIL import Image

from config import DATA_DIR

THUMBNAIL_DIR = Path(DATA_DIR) / "thumbnails"
THUMBNAIL_MAX_SIZE = 120  # px — longest edge


def _thumb_cache_path(source: Path) -> Path:
    """Unique cache filename based on source name + mtime."""
    key = f"{source.name}:{source.stat().st_mtime_ns}"
    digest = hashlib.sha256(key.encode()).hexdigest()[:16]
    return THUMBNAIL_DIR / f"{source.stem}_{digest}.jpg"


def get_or_create_thumbnail(source: Path) -> Path:
    """
    Return path to a cached JPEG thumbnail (~120px).

    Regenerates if the source file is newer than the cached thumb.
    """
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    thumb_path = _thumb_cache_path(source)

    if thumb_path.is_file():
        return thumb_path

    with Image.open(source) as img:
        img = img.convert("RGB")
        img.thumbnail((THUMBNAIL_MAX_SIZE, THUMBNAIL_MAX_SIZE), Image.Resampling.LANCZOS)
        img.save(thumb_path, format="JPEG", quality=75, optimize=True)

    return thumb_path


def delete_thumbnail(source: Path) -> None:
    """Remove cached thumbnail(s) for a deleted library image."""
    if not THUMBNAIL_DIR.is_dir():
        return
    for thumb in THUMBNAIL_DIR.glob(f"{source.stem}_*.jpg"):
        thumb.unlink(missing_ok=True)

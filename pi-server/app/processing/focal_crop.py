"""Face-aware vertical crop positioning for cover-scale resizing."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Vertical fallback when no face is found: 35% into the available crop range
LANDSCAPE_FALLBACK_RATIO = 0.35

_haar_cascade: cv2.CascadeClassifier | None = None


def _get_face_detector() -> cv2.CascadeClassifier:
    global _haar_cascade
    if _haar_cascade is None:
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        _haar_cascade = cv2.CascadeClassifier(str(cascade_path))
    return _haar_cascade


def cover_scale_size(src_w: int, src_h: int, target_w: int, target_h: int) -> tuple[int, int, float]:
    """Return scaled dimensions and uniform cover scale factor."""
    scale = max(target_w / src_w, target_h / src_h)
    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))
    return new_w, new_h, scale


def detect_face_centers_y(rgb_image: np.ndarray) -> list[float]:
    """
    Detect frontal faces and return their vertical centers in pixel coordinates.

    rgb_image: HxWx3 uint8 RGB array
    """
    gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
    detector = _get_face_detector()
    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(30, 30),
    )
    if len(faces) == 0:
        return []

    centers = [float(y + h / 2.0) for x, y, w, h in faces]
    logger.debug("Detected %d face(s) at y=%s", len(centers), centers)
    return centers


def compute_vertical_crop_top(
    scaled_h: int,
    crop_h: int,
    *,
    focal_y: float | None = None,
    fallback_ratio: float = LANDSCAPE_FALLBACK_RATIO,
) -> int:
    """
    Compute the top coordinate for a crop_h window inside a scaled_h image.

    focal_y      — vertical center to protect (face midpoint on scaled image)
    fallback_ratio — position in [0, 1] along available range when no face
    """
    if scaled_h <= crop_h:
        return 0

    max_top = scaled_h - crop_h
    if focal_y is not None:
        top = int(round(focal_y - crop_h / 2.0))
    else:
        top = int(round(max_top * fallback_ratio))

    return max(0, min(top, max_top))


def compute_focal_crop_box(
    scaled_w: int,
    scaled_h: int,
    target_w: int,
    target_h: int,
    face_centers_y: list[float],
) -> tuple[int, int, int, int]:
    """Return PIL crop box (left, top, right, bottom) for the target viewport."""
    focal_y = float(np.mean(face_centers_y)) if face_centers_y else None
    left = max(0, (scaled_w - target_w) // 2)
    top = compute_vertical_crop_top(scaled_h, target_h, focal_y=focal_y)
    return left, top, left + target_w, top + target_h


def resize_cover_focal(image: Image.Image, width: int, height: int) -> Image.Image:
    """
    Cover-scale to maximize real estate, then crop with face-aware vertical shift.

    Horizontal crop stays centered. Vertical crop centers on detected faces when
    present; otherwise uses a top-weighted fallback for landscapes.
    """
    src = image.convert("RGB")
    src_w, src_h = src.size
    new_w, new_h, _ = cover_scale_size(src_w, src_h, width, height)

    resized = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
    rgb = np.array(resized, dtype=np.uint8)

    face_centers_y = detect_face_centers_y(rgb)
    if face_centers_y:
        logger.info("Focal crop: aligning to %d detected face(s)", len(face_centers_y))
    else:
        logger.info("Focal crop: no faces — using %.0f%% top-weighted fallback", LANDSCAPE_FALLBACK_RATIO * 100)

    crop_box = compute_focal_crop_box(new_w, new_h, width, height, face_centers_y)
    return resized.crop(crop_box)

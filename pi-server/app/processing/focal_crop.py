"""Orientation-aware resize, crop, and pad for the 800×480 e-ink frame."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from processing.color import PERCEPTUAL_CHANNEL_WEIGHTS

logger = logging.getLogger(__name__)

# Vertical fallback when no face is found (landscape horizontal crop uses center)
LANDSCAPE_FALLBACK_RATIO = 0.35
PORTRAIT_VERT_OVERSCALE = 1.08
LUMINANCE_PAD_THRESHOLD = 127

_haar_cascade: cv2.CascadeClassifier | None = None


def _get_face_detector() -> cv2.CascadeClassifier:
    global _haar_cascade
    if _haar_cascade is None:
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        _haar_cascade = cv2.CascadeClassifier(str(cascade_path))
    return _haar_cascade


def scale_to_height(src_w: int, src_h: int, target_h: int) -> tuple[int, int, float]:
    """Uniform scale so the image height matches target_h."""
    scale = target_h / src_h
    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))
    return new_w, new_h, scale


def average_luminance(rgb: np.ndarray) -> float:
    """Perceptual mean brightness in [0, 255]."""
    flat = rgb.reshape(-1, 3).astype(np.float32)
    return float(np.mean(flat @ PERCEPTUAL_CHANNEL_WEIGHTS))


def adaptive_pad_color(rgb: np.ndarray) -> tuple[int, int, int]:
    """White padding for bright photos, black for dark."""
    if average_luminance(rgb) > LUMINANCE_PAD_THRESHOLD:
        return (255, 255, 255)
    return (0, 0, 0)


def detect_face_centers(rgb_image: np.ndarray) -> list[tuple[float, float]]:
    """
    Detect frontal faces and return (center_x, center_y) in pixel coordinates.

    rgb_image: H×W×3 uint8 RGB array
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

    centers = [(float(x + w / 2.0), float(y + h / 2.0)) for x, y, w, h in faces]
    logger.debug("Detected %d face(s) at %s", len(centers), centers)
    return centers


def compute_vertical_crop_top(
    scaled_h: int,
    crop_h: int,
    *,
    focal_y: float | None = None,
    fallback_ratio: float = LANDSCAPE_FALLBACK_RATIO,
) -> int:
    """Top coordinate for a crop_h window inside a scaled_h image."""
    if scaled_h <= crop_h:
        return 0

    max_top = scaled_h - crop_h
    if focal_y is not None:
        top = int(round(focal_y - crop_h / 2.0))
    else:
        top = int(round(max_top * fallback_ratio))

    return max(0, min(top, max_top))


def compute_horizontal_crop_left(
    scaled_w: int,
    crop_w: int,
    *,
    focal_x: float | None = None,
    fallback_ratio: float = 0.5,
) -> int:
    """Left coordinate for a crop_w window inside a scaled_w image."""
    if scaled_w <= crop_w:
        return 0

    max_left = scaled_w - crop_w
    if focal_x is not None:
        left = int(round(focal_x - crop_w / 2.0))
    else:
        left = int(round(max_left * fallback_ratio))

    return max(0, min(left, max_left))


def compute_paste_x(
    canvas_w: int,
    content_w: int,
    *,
    focal_x: float | None = None,
) -> int:
    """Horizontal paste offset that centers content, or the face, on the canvas."""
    max_x = canvas_w - content_w
    if max_x <= 0:
        return 0

    if focal_x is not None:
        paste_x = int(round(canvas_w / 2.0 - focal_x))
    else:
        paste_x = max_x // 2

    return max(0, min(paste_x, max_x))


def _mean_axis(values: list[float]) -> float | None:
    return float(np.mean(values)) if values else None


def _layout_landscape(
    image: Image.Image,
    target_w: int,
    target_h: int,
    original_rgb: np.ndarray,
) -> Image.Image:
    """
    Landscape (width > height): scale to target_h, then crop or pad to target_w.

    Face detection shifts the horizontal viewport; vertical dimension is already exact.
    """
    src_w, src_h = image.size
    new_w, new_h, _ = scale_to_height(src_w, src_h, target_h)
    resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    rgb = np.array(resized, dtype=np.uint8)

    faces = detect_face_centers(rgb)
    focal_x = _mean_axis([cx for cx, _ in faces])

    if faces:
        logger.info("Landscape layout: aligning to %d detected face(s)", len(faces))
    else:
        logger.info("Landscape layout: no faces — center crop")

    if new_w > target_w:
        left = compute_horizontal_crop_left(new_w, target_w, focal_x=focal_x)
        return resized.crop((left, 0, left + target_w, target_h))

    if new_w == target_w:
        return resized

    pad_color = adaptive_pad_color(original_rgb)
    canvas = Image.new("RGB", (target_w, target_h), pad_color)
    paste_x = compute_paste_x(target_w, new_w, focal_x=focal_x)
    canvas.paste(resized, (paste_x, 0))
    logger.info("Landscape layout: padded %d px with %s", target_w - new_w, pad_color)
    return canvas


def _layout_portrait_pad(
    image: Image.Image,
    target_w: int,
    target_h: int,
    original_rgb: np.ndarray,
) -> Image.Image:
    """
    Portrait / square / tall: height-fit with slight vertical crop, adaptive side padding.

    Scales taller than the frame to allow a face-aware vertical trim, then letterboxes
    onto an 800×480 canvas without zooming to fill the full width.
    """
    src_w, src_h = image.size
    overscaled_h = int(round(target_h * PORTRAIT_VERT_OVERSCALE))
    scale = overscaled_h / src_h
    new_w = max(1, int(round(src_w * scale)))
    new_h = max(1, int(round(src_h * scale)))

    resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    rgb = np.array(resized, dtype=np.uint8)

    faces = detect_face_centers(rgb)
    focal_y = _mean_axis([cy for _, cy in faces])
    focal_x = _mean_axis([cx for cx, _ in faces])

    top = compute_vertical_crop_top(new_h, target_h, focal_y=focal_y)
    cropped = resized.crop((0, top, new_w, top + target_h))

    if faces:
        logger.info("Portrait layout: %d face(s), vertical crop top=%d", len(faces), top)
    else:
        logger.info("Portrait layout: no faces — top-weighted vertical crop top=%d", top)

    pad_color = adaptive_pad_color(original_rgb)
    canvas = Image.new("RGB", (target_w, target_h), pad_color)
    adjusted_focal_x = (focal_x - 0) if focal_x is not None else None
    paste_x = compute_paste_x(target_w, new_w, focal_x=adjusted_focal_x)
    canvas.paste(cropped, (paste_x, 0))
    logger.info("Portrait layout: padded %d px with %s", target_w - new_w, pad_color)
    return canvas


def resize_smart_focal(image: Image.Image, width: int, height: int) -> Image.Image:
    """
    Fit any aspect ratio to the display with orientation-specific rules.

    landscape (w > h) — height-fit, face-aware horizontal crop/pad
    portrait/square/tall (h >= w) — hybrid vertical crop + adaptive side padding
    """
    src = image.convert("RGB")
    src_w, src_h = src.size
    original_rgb = np.array(src, dtype=np.uint8)

    if src_w > src_h:
        return _layout_landscape(src, width, height, original_rgb)
    return _layout_portrait_pad(src, width, height, original_rgb)


# Backward-compatible alias for callers/tests
resize_cover_focal = resize_smart_focal

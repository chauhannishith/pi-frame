"""Palette quantization with optional error-diffusion dithering."""

import numpy as np
from PIL import Image

from config import FLOYD_STEINBERG_ERROR_DAMPING
from palette import EINK_PALETTE_RGB
from processing.color import match_pixel_to_palette, nearest_palette_indices
from processing.types import DitherMethod


def quantize_nearest(rgb_image: np.ndarray, palette_rgb: np.ndarray) -> np.ndarray:
    """Map each pixel to the nearest palette color with no dithering."""
    return nearest_palette_indices(rgb_image, palette_rgb)


def _diffuse_floyd_steinberg_error(
    working: np.ndarray,
    y: int,
    x: int,
    error: np.ndarray,
    reverse: bool,
    h: int,
    w: int,
) -> None:
    """Spread quantization error to neighbors, respecting serpentine scan direction."""
    error = error * FLOYD_STEINBERG_ERROR_DAMPING

    if not reverse:
        if x + 1 < w:
            working[y, x + 1] += error * (7 / 16)
        if y + 1 < h:
            if x - 1 >= 0:
                working[y + 1, x - 1] += error * (3 / 16)
            working[y + 1, x] += error * (5 / 16)
            if x + 1 < w:
                working[y + 1, x + 1] += error * (1 / 16)
    else:
        if x - 1 >= 0:
            working[y, x - 1] += error * (7 / 16)
        if y + 1 < h:
            if x + 1 < w:
                working[y + 1, x + 1] += error * (3 / 16)
            working[y + 1, x] += error * (5 / 16)
            if x - 1 >= 0:
                working[y + 1, x - 1] += error * (1 / 16)


def quantize_floyd_steinberg(rgb_image: np.ndarray, palette_rgb: np.ndarray) -> np.ndarray:
    """
    Floyd-Steinberg with serpentine scanning, perceptual palette matching,
    and damped error diffusion to reduce green bleed on warm skin tones.
    """
    h, w, _ = rgb_image.shape
    working = rgb_image.astype(np.float32).copy()
    indices = np.zeros((h, w), dtype=np.uint8)

    for y in range(h):
        reverse = y % 2 == 1
        x_range = range(w - 1, -1, -1) if reverse else range(w)

        for x in x_range:
            old = working[y, x].copy()
            idx, matched = match_pixel_to_palette(old, palette_rgb)
            indices[y, x] = idx
            error = old - matched
            _diffuse_floyd_steinberg_error(working, y, x, error, reverse, h, w)

    return indices


def quantize_atkinson(rgb_image: np.ndarray, palette_rgb: np.ndarray) -> np.ndarray:
    """Atkinson error diffusion with perceptual palette matching."""
    h, w, _ = rgb_image.shape
    working = rgb_image.astype(np.float32).copy()
    indices = np.zeros((h, w), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            old = working[y, x].copy()
            idx, matched = match_pixel_to_palette(old, palette_rgb)
            indices[y, x] = idx
            error = (old - matched) / 8.0

            neighbors = [
                (y, x + 1),
                (y, x + 2),
                (y + 1, x - 1),
                (y + 1, x),
                (y + 1, x + 1),
                (y + 2, x),
            ]
            for ny, nx in neighbors:
                if 0 <= ny < h and 0 <= nx < w:
                    working[ny, nx] += error

    return indices


def quantize_to_palette(
    image: Image.Image,
    palette_rgb: np.ndarray | None = None,
    method: DitherMethod | str = "floyd_steinberg",
) -> np.ndarray:
    """
    Quantize an RGB PIL image to palette indices (HxW uint8 array).

    Floyd-Steinberg uses serpentine scanning, 80% error damping, and
    perceptual channel weights for palette selection.
    """
    palette_rgb = palette_rgb if palette_rgb is not None else EINK_PALETTE_RGB
    rgb = np.array(image.convert("RGB"), dtype=np.float32)

    method = str(method).lower()
    if method == "nearest":
        return quantize_nearest(rgb, palette_rgb)
    if method == "atkinson":
        return quantize_atkinson(rgb, palette_rgb)
    return quantize_floyd_steinberg(rgb, palette_rgb)


def indices_to_preview_rgb(indices: np.ndarray, palette_rgb: np.ndarray | None = None) -> np.ndarray:
    """Expand palette indices back to an RGB preview image."""
    palette = palette_rgb if palette_rgb is not None else EINK_PALETTE_RGB
    return palette[indices].astype(np.uint8)

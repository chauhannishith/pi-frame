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


def _spread_error(
    working: np.ndarray,
    indices: np.ndarray,
    y: int,
    x: int,
    error: np.ndarray,
    palette_rgb: np.ndarray,
    diffusion_mask: np.ndarray,
    neighbors: list[tuple[int, int, float]],
) -> None:
    h, w, _ = working.shape
    for ny, nx, weight in neighbors:
        if 0 <= ny < h and 0 <= nx < w and diffusion_mask[ny, nx]:
            working[ny, nx] += error * weight


def quantize_floyd_steinberg(
    rgb_image: np.ndarray,
    palette_rgb: np.ndarray,
    diffusion_mask: np.ndarray | None = None,
) -> np.ndarray:
    """
    Floyd-Steinberg with serpentine scanning, perceptual palette matching,
    and damped error diffusion to reduce green bleed on warm skin tones.
    """
    h, w, _ = rgb_image.shape
    working = rgb_image.astype(np.float32).copy()
    indices = np.zeros((h, w), dtype=np.uint8)
    if diffusion_mask is None:
        diffusion_mask = np.ones((h, w), dtype=bool)

    for y in range(h):
        reverse = y % 2 == 1
        x_range = range(w - 1, -1, -1) if reverse else range(w)

        for x in x_range:
            old = working[y, x].copy()
            idx, matched = match_pixel_to_palette(old, palette_rgb)
            indices[y, x] = idx
            if not diffusion_mask[y, x]:
                working[y, x] = matched
                continue

            error = old - matched
            if not reverse:
                neighbors = [
                    (y, x + 1, 7 / 16),
                    (y + 1, x - 1, 3 / 16),
                    (y + 1, x, 5 / 16),
                    (y + 1, x + 1, 1 / 16),
                ]
            else:
                neighbors = [
                    (y, x - 1, 7 / 16),
                    (y + 1, x + 1, 3 / 16),
                    (y + 1, x, 5 / 16),
                    (y + 1, x - 1, 1 / 16),
                ]
            _spread_error(working, indices, y, x, error * FLOYD_STEINBERG_ERROR_DAMPING, palette_rgb, diffusion_mask, neighbors)

    return indices


def quantize_atkinson(
    rgb_image: np.ndarray,
    palette_rgb: np.ndarray,
    diffusion_mask: np.ndarray | None = None,
) -> np.ndarray:
    """Atkinson error diffusion with perceptual palette matching."""
    h, w, _ = rgb_image.shape
    working = rgb_image.astype(np.float32).copy()
    indices = np.zeros((h, w), dtype=np.uint8)
    if diffusion_mask is None:
        diffusion_mask = np.ones((h, w), dtype=bool)

    for y in range(h):
        for x in range(w):
            old = working[y, x].copy()
            idx, matched = match_pixel_to_palette(old, palette_rgb)
            indices[y, x] = idx
            if not diffusion_mask[y, x]:
                working[y, x] = matched
                continue

            error = (old - matched) / 8.0
            neighbors = [
                (y, x + 1, 1.0),
                (y, x + 2, 1.0),
                (y + 1, x - 1, 1.0),
                (y + 1, x, 1.0),
                (y + 1, x + 1, 1.0),
                (y + 2, x, 1.0),
            ]
            _spread_error(working, indices, y, x, error, palette_rgb, diffusion_mask, neighbors)

    return indices


def composite_indices_on_frame(
    content_indices: np.ndarray,
    frame_width: int,
    frame_height: int,
    paste_x: int,
    paste_y: int,
    pad_index: int,
) -> np.ndarray:
    """Place dithered content onto a full-frame index buffer filled with pad_index."""
    frame = np.full((frame_height, frame_width), pad_index, dtype=np.uint8)
    content_h, content_w = content_indices.shape
    frame[paste_y : paste_y + content_h, paste_x : paste_x + content_w] = content_indices
    return frame


def palette_index_for_rgb(
    rgb: tuple[int, int, int],
    palette_rgb: np.ndarray,
) -> int:
    color = np.array(rgb, dtype=np.float32)
    idx, _ = match_pixel_to_palette(color, palette_rgb)
    return int(idx)


def quantize_to_palette(
    image: Image.Image,
    palette_rgb: np.ndarray | None = None,
    method: DitherMethod | str = "floyd_steinberg",
    diffusion_mask: np.ndarray | None = None,
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
        return quantize_atkinson(rgb, palette_rgb, diffusion_mask=diffusion_mask)
    return quantize_floyd_steinberg(rgb, palette_rgb, diffusion_mask=diffusion_mask)


def indices_to_preview_rgb(indices: np.ndarray, palette_rgb: np.ndarray | None = None) -> np.ndarray:
    """Expand palette indices back to an RGB preview image."""
    palette = palette_rgb if palette_rgb is not None else EINK_PALETTE_RGB
    return palette[indices].astype(np.uint8)

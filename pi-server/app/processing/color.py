"""Perceptual color matching and optional CIE L*a*b* utilities."""

import numpy as np

from palette import EINK_PALETTE_RGB

# ITU-R BT.601 luma weights — eyes are most sensitive to green
PERCEPTUAL_CHANNEL_WEIGHTS = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def perceptual_color_distance(
    rgb: np.ndarray,
    palette_rgb: np.ndarray,
    weights: np.ndarray | None = None,
) -> np.ndarray:
    """
    Weighted squared RGB distance from rgb to each palette swatch.

    rgb: (N, 3) or (3,)
    returns: (N, num_colors) or (num_colors,)
    """
    weights = weights if weights is not None else PERCEPTUAL_CHANNEL_WEIGHTS
    rgb = np.atleast_2d(rgb)
    diff = palette_rgb[np.newaxis, :, :] - rgb[:, np.newaxis, :]
    distances = np.sum(weights * (diff ** 2), axis=2)
    return distances[0] if distances.shape[0] == 1 else distances


def nearest_palette_index(pixel_rgb: np.ndarray, palette_rgb: np.ndarray) -> int:
    """Return the palette index closest to a single RGB pixel."""
    return int(np.argmin(perceptual_color_distance(pixel_rgb, palette_rgb)))


def nearest_palette_indices(
    rgb_image: np.ndarray,
    palette_rgb: np.ndarray,
    palette_lab: np.ndarray | None = None,
) -> np.ndarray:
    """Map each pixel to the closest palette index using perceptual RGB weights."""
    del palette_lab
    flat = rgb_image.reshape(-1, 3)
    diff = palette_rgb[np.newaxis, :, :] - flat[:, np.newaxis, :]
    distances = np.sum(PERCEPTUAL_CHANNEL_WEIGHTS * (diff ** 2), axis=2)
    return np.argmin(distances, axis=1).astype(np.uint8).reshape(rgb_image.shape[:2])


def match_pixel_to_palette(
    pixel_rgb: np.ndarray,
    palette_rgb: np.ndarray,
    palette_lab: np.ndarray | None = None,
) -> tuple[int, np.ndarray]:
    """Return palette index and RGB swatch for a single pixel."""
    del palette_lab
    idx = nearest_palette_index(pixel_rgb, palette_rgb)
    return idx, palette_rgb[idx]


# ---------------------------------------------------------------------------
# CIE L*a*b* (retained for tests / future use)
# ---------------------------------------------------------------------------


def srgb_to_linear(channel: np.ndarray) -> np.ndarray:
    normalized = channel / 255.0
    return np.where(
        normalized <= 0.04045,
        normalized / 12.92,
        ((normalized + 0.055) / 1.055) ** 2.4,
    )


def rgb_to_lab_cie(rgb: np.ndarray) -> np.ndarray:
    """Convert RGB (0-255) to CIE L*a*b*."""
    rgb = np.clip(rgb, 0, 255).astype(np.float64)
    linear = srgb_to_linear(rgb)
    r, g, b = linear[..., 0], linear[..., 1], linear[..., 2]

    x = r * 0.4124564 + g * 0.3575761 + b * 0.1804375
    y = r * 0.2126729 + g * 0.7151522 + b * 0.0721750
    z = r * 0.0193339 + g * 0.1191920 + b * 0.9503041

    x_ref, y_ref, z_ref = x / 0.95047, y / 1.0, z / 1.08883
    epsilon = (6.0 / 29.0) ** 3
    kappa = (29.0 / 6.0) ** 2 / 3.0

    def _f(component: np.ndarray) -> np.ndarray:
        return np.where(component > epsilon, component ** (1.0 / 3.0), kappa * component + 4.0 / 29.0)

    fx, fy, fz = _f(x_ref), _f(y_ref), _f(z_ref)
    L = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return np.stack([L, a, b], axis=-1).astype(np.float32)


def build_palette_lab(palette_rgb: np.ndarray | None = None) -> np.ndarray:
    """Pre-compute CIE L*a*b* coordinates for every palette swatch."""
    palette = palette_rgb if palette_rgb is not None else EINK_PALETTE_RGB
    swatches = palette.reshape(-1, 1, 3)
    return rgb_to_lab_cie(swatches).reshape(-1, 3)

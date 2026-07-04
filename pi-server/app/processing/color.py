"""CIE L*a*b* color conversion and palette matching."""

import numpy as np

from palette import EINK_PALETTE_RGB


def srgb_to_linear(channel: np.ndarray) -> np.ndarray:
    normalized = channel / 255.0
    return np.where(
        normalized <= 0.04045,
        normalized / 12.92,
        ((normalized + 0.055) / 1.055) ** 2.4,
    )


def rgb_to_lab_cie(rgb: np.ndarray) -> np.ndarray:
    """Convert RGB (0-255) to CIE L*a*b* for perceptual color matching."""
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


def nearest_palette_indices(
    rgb_image: np.ndarray,
    palette_rgb: np.ndarray,
    palette_lab: np.ndarray | None = None,
) -> np.ndarray:
    """Map each pixel to the closest palette index using CIE76 delta E."""
    if palette_lab is None:
        palette_lab = build_palette_lab(palette_rgb)

    lab_image = rgb_to_lab_cie(rgb_image)
    flat = lab_image.reshape(-1, 3)
    distances = np.linalg.norm(
        flat[:, np.newaxis, :] - palette_lab[np.newaxis, :, :],
        axis=2,
    )
    return np.argmin(distances, axis=1).astype(np.uint8).reshape(rgb_image.shape[:2])


def match_pixel_to_palette(
    pixel_rgb: np.ndarray,
    palette_rgb: np.ndarray,
    palette_lab: np.ndarray,
) -> tuple[int, np.ndarray]:
    """Return palette index and RGB swatch for a single pixel."""
    pixel_lab = rgb_to_lab_cie(pixel_rgb.reshape(1, 1, 3))[0, 0]
    idx = int(np.argmin(np.linalg.norm(palette_lab - pixel_lab, axis=1)))
    return idx, palette_rgb[idx]

"""
Image processing pipeline: resize, LAB-space palette quantization with
error diffusion, and raw binary frame export.
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image

from config import BINARY_PACK_MODE, DITHER_METHOD, FRAME_HEIGHT, FRAME_WIDTH
from palette import EINK_PALETTE_RGB, NUM_COLORS

logger = logging.getLogger(__name__)

DitherMethod = Literal["floyd_steinberg", "atkinson", "nearest"]
PackMode = Literal["byte", "packed"]


class ResizeMode(str, Enum):
    COVER = "cover"
    CONTAIN = "contain"
    STRETCH = "stretch"


def _srgb_to_linear(channel: np.ndarray) -> np.ndarray:
    normalized = channel / 255.0
    return np.where(
        normalized <= 0.04045,
        normalized / 12.92,
        ((normalized + 0.055) / 1.055) ** 2.4,
    )


def rgb_to_lab_cie(rgb: np.ndarray) -> np.ndarray:
    """Convert RGB (0-255) to CIE L*a*b* for perceptual color matching."""
    rgb = np.clip(rgb, 0, 255).astype(np.float64)
    linear = _srgb_to_linear(rgb)
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
    """
    Map each pixel to the closest palette index using CIE76 delta E in L*a*b*.
    """
    if palette_lab is None:
        palette_lab = build_palette_lab(palette_rgb)

    lab_image = rgb_to_lab_cie(rgb_image)
    flat = lab_image.reshape(-1, 3)
    distances = np.linalg.norm(
        flat[:, np.newaxis, :] - palette_lab[np.newaxis, :, :],
        axis=2,
    )
    return np.argmin(distances, axis=1).astype(np.uint8).reshape(rgb_image.shape[:2])


def resize_for_display(
    image: Image.Image,
    width: int,
    height: int,
    mode: ResizeMode | str = ResizeMode.COVER,
) -> Image.Image:
    """
    Resize source image to target display dimensions.

    cover   — scale to fill, center-crop (best for photos)
    contain — scale to fit inside, letterbox with white
    stretch — ignore aspect ratio
    """
    mode = ResizeMode(mode)
    src = image.convert("RGB")

    if mode == ResizeMode.STRETCH:
        return src.resize((width, height), Image.Resampling.LANCZOS)

    src_w, src_h = src.size
    if mode == ResizeMode.CONTAIN:
        scale = min(width / src_w, height / src_h)
        new_w = max(1, int(src_w * scale))
        new_h = max(1, int(src_h * scale))
        resized = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", (width, height), (255, 255, 255))
        offset = ((width - new_w) // 2, (height - new_h) // 2)
        canvas.paste(resized, offset)
        return canvas

    # cover
    scale = max(width / src_w, height / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    resized = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _match_pixel_to_palette(
    pixel_rgb: np.ndarray,
    palette_rgb: np.ndarray,
    palette_lab: np.ndarray,
) -> tuple[int, np.ndarray]:
    """Return palette index and RGB swatch for a single pixel using CIE76."""
    pixel_lab = rgb_to_lab_cie(pixel_rgb.reshape(1, 1, 3))[0, 0]
    idx = int(np.argmin(np.linalg.norm(palette_lab - pixel_lab, axis=1)))
    return idx, palette_rgb[idx]


def _quantize_nearest(rgb_image: np.ndarray, palette_rgb: np.ndarray, palette_lab: np.ndarray) -> np.ndarray:
    return nearest_palette_indices(rgb_image, palette_rgb, palette_lab)


def _quantize_floyd_steinberg(
    rgb_image: np.ndarray,
    palette_rgb: np.ndarray,
    palette_lab: np.ndarray,
) -> np.ndarray:
    """Floyd-Steinberg error diffusion; palette match in L*a*b*, error in RGB."""
    h, w, _ = rgb_image.shape
    working = rgb_image.astype(np.float32).copy()
    indices = np.zeros((h, w), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            old = working[y, x].copy()
            idx, matched = _match_pixel_to_palette(old, palette_rgb, palette_lab)
            indices[y, x] = idx
            error = old - matched

            if x + 1 < w:
                working[y, x + 1] += error * (7 / 16)
            if y + 1 < h:
                if x > 0:
                    working[y + 1, x - 1] += error * (3 / 16)
                working[y + 1, x] += error * (5 / 16)
                if x + 1 < w:
                    working[y + 1, x + 1] += error * (1 / 16)

    return indices


def _quantize_atkinson(
    rgb_image: np.ndarray,
    palette_rgb: np.ndarray,
    palette_lab: np.ndarray,
) -> np.ndarray:
    """Atkinson error diffusion; palette match in L*a*b*, error in RGB."""
    h, w, _ = rgb_image.shape
    working = rgb_image.astype(np.float32).copy()
    indices = np.zeros((h, w), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            old = working[y, x].copy()
            idx, matched = _match_pixel_to_palette(old, palette_rgb, palette_lab)
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

    Uses perceptual LAB distance; default method is Floyd-Steinberg dithering.
    """
    palette_rgb = palette_rgb if palette_rgb is not None else EINK_PALETTE_RGB
    palette_lab = build_palette_lab(palette_rgb)
    rgb = np.array(image.convert("RGB"), dtype=np.float32)

    method = str(method).lower()
    if method == "nearest":
        return _quantize_nearest(rgb, palette_rgb, palette_lab)
    if method == "atkinson":
        return _quantize_atkinson(rgb, palette_rgb, palette_lab)
    return _quantize_floyd_steinberg(rgb, palette_rgb, palette_lab)


def indices_to_preview_rgb(indices: np.ndarray, palette_rgb: np.ndarray | None = None) -> np.ndarray:
    """Expand palette indices back to an RGB preview image."""
    palette = palette_rgb if palette_rgb is not None else EINK_PALETTE_RGB
    return palette[indices].astype(np.uint8)


def pack_indices_byte(indices: np.ndarray) -> bytes:
    """One palette index (0-5) per byte — simple firmware-friendly layout."""
    if indices.max(initial=0) >= NUM_COLORS:
        raise ValueError(f"Palette index out of range (max {NUM_COLORS - 1})")
    return indices.astype(np.uint8).tobytes()


def pack_indices_packed(indices: np.ndarray) -> bytes:
    """
    Pack 3-bit palette indices: 8 pixels into 3 bytes (24 bits total).

    Bit order within each byte group: pixel0 MSB nibble-first in 3-bit slots.
    """
    flat = indices.flatten().astype(np.uint8)
    if flat.max(initial=0) >= NUM_COLORS:
        raise ValueError(f"Palette index out of range (max {NUM_COLORS - 1})")

    pad = (8 - len(flat) % 8) % 8
    if pad:
        flat = np.concatenate([flat, np.zeros(pad, dtype=np.uint8)])

    out = bytearray()
    for i in range(0, len(flat), 8):
        p = flat[i : i + 8]
        out.append((int(p[0]) << 5) | (int(p[1]) << 2) | (int(p[2]) >> 1))
        out.append(((int(p[2]) & 1) << 7) | (int(p[3]) << 4) | (int(p[4]) << 1) | (int(p[5]) >> 2))
        out.append(((int(p[5]) & 3) << 6) | (int(p[6]) << 3) | int(p[7]))
    return bytes(out)


def unpack_indices_byte(data: bytes, width: int, height: int) -> np.ndarray:
    """Reverse pack_indices_byte."""
    expected = width * height
    if len(data) != expected:
        raise ValueError(f"Expected {expected} bytes, got {len(data)}")
    return np.frombuffer(data, dtype=np.uint8).reshape(height, width)


def unpack_indices_packed(data: bytes, width: int, height: int) -> np.ndarray:
    """Reverse pack_indices_packed."""
    pixel_count = width * height
    padded = ((pixel_count + 7) // 8) * 8
    expected_bytes = padded * 3 // 8
    if len(data) != expected_bytes:
        raise ValueError(f"Expected {expected_bytes} bytes, got {len(data)}")

    flat = np.zeros(padded, dtype=np.uint8)
    byte_idx = 0
    for i in range(0, padded, 8):
        b0, b1, b2 = data[byte_idx], data[byte_idx + 1], data[byte_idx + 2]
        byte_idx += 3
        flat[i + 0] = (b0 >> 5) & 0x7
        flat[i + 1] = (b0 >> 2) & 0x7
        flat[i + 2] = ((b0 & 0x3) << 1) | ((b1 >> 7) & 0x1)
        flat[i + 3] = (b1 >> 4) & 0x7
        flat[i + 4] = (b1 >> 1) & 0x7
        flat[i + 5] = ((b1 & 0x1) << 2) | ((b2 >> 6) & 0x3)
        flat[i + 6] = (b2 >> 3) & 0x7
        flat[i + 7] = b2 & 0x7

    return flat[:pixel_count].reshape(height, width)


def pack_frame_buffer(indices: np.ndarray, mode: PackMode | str = "byte") -> bytes:
    mode = str(mode).lower()
    if mode == "packed":
        return pack_indices_packed(indices)
    return pack_indices_byte(indices)


def unpack_frame_buffer(data: bytes, width: int, height: int, mode: PackMode | str = "byte") -> np.ndarray:
    mode = str(mode).lower()
    if mode == "packed":
        return unpack_indices_packed(data, width, height)
    return unpack_indices_byte(data, width, height)


def process_image_to_binary(
    source: str | Path,
    output: str | Path,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
    *,
    resize_mode: ResizeMode | str = ResizeMode.COVER,
    dither_method: DitherMethod | str = DITHER_METHOD,
    pack_mode: PackMode | str = BINARY_PACK_MODE,
    palette_rgb: np.ndarray | None = None,
) -> Path:
    """
    Full pipeline: load → resize → quantize → write raw binary frame buffer.

    Returns the output path.
    """
    source_path = Path(source)
    output_path = Path(output)

    if not source_path.is_file():
        raise FileNotFoundError(f"Source image not found: {source_path}")

    logger.info(
        "Processing %s -> %s (%dx%d, dither=%s, pack=%s)",
        source_path,
        output_path,
        width,
        height,
        dither_method,
        pack_mode,
    )

    with Image.open(source_path) as img:
        resized = resize_for_display(img, width, height, mode=resize_mode)

    indices = quantize_to_palette(
        resized,
        palette_rgb=palette_rgb,
        method=dither_method,
    )

    frame_bytes = pack_frame_buffer(indices, mode=pack_mode)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(frame_bytes)

    logger.info("Wrote %d bytes to %s", len(frame_bytes), output_path)
    return output_path


def find_latest_source_image(source_dir: str | Path) -> Path | None:
    """Return the most recently modified supported image in source_dir."""
    from config import SUPPORTED_IMAGE_EXTENSIONS

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


def run_daily_processing(
    source_dir: str | Path,
    output_path: str | Path,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
) -> None:
    """Process the newest source image and write the frame binary."""
    source = find_latest_source_image(source_dir)
    if source is None:
        logger.warning("No source images found in %s", source_dir)
        return

    process_image_to_binary(source, output_path, width=width, height=height)

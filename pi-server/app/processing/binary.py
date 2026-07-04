"""Pack and unpack palette index matrices as raw binary frame buffers."""

import numpy as np

from palette import NUM_COLORS
from processing.types import PackMode


def pack_indices_byte(indices: np.ndarray) -> bytes:
    """One palette index (0-5) per byte — simple firmware-friendly layout."""
    if indices.max(initial=0) >= NUM_COLORS:
        raise ValueError(f"Palette index out of range (max {NUM_COLORS - 1})")
    return indices.astype(np.uint8).tobytes()


def pack_indices_packed(indices: np.ndarray) -> bytes:
    """Pack 3-bit palette indices: 8 pixels into 3 bytes (24 bits total)."""
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

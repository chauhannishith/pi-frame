"""Frame orientation — landscape (native) or portrait (rotated 90°)."""

from __future__ import annotations

import numpy as np

from config import FRAME_HEIGHT, FRAME_WIDTH

ORIENTATIONS = ("landscape", "portrait")


def normalize_orientation(value: str | None) -> str:
    if value and str(value).lower() in ORIENTATIONS:
        return str(value).lower()
    return "landscape"


def orientation_label(value: str | None) -> str:
    return normalize_orientation(value).capitalize()


def processing_dimensions(
    orientation: str | None,
    width: int = FRAME_WIDTH,
    height: int = FRAME_HEIGHT,
) -> tuple[int, int]:
    """Width and height used for resize/dither before rotation."""
    if normalize_orientation(orientation) == "portrait":
        return height, width
    return width, height


def output_dimensions() -> tuple[int, int]:
    """Default binary and preview size (native panel)."""
    return FRAME_WIDTH, FRAME_HEIGHT


def orient_indices(indices: np.ndarray, orientation: str | None) -> np.ndarray:
    """Rotate portrait processing output to native 800×480 layout."""
    if normalize_orientation(orientation) == "portrait":
        return np.rot90(indices, k=-1)
    return indices

"""
Image processing package for the 6-color e-ink frame.

Modules:
  color    — perceptual palette matching (ITU-R BT.601 weights)
  resize   — scale, crop, and letterbox to display dimensions
  dither   — palette quantization with error diffusion
  binary   — raw frame buffer packing
  sources  — source image discovery
  pipeline — end-to-end orchestration
"""

from processing.binary import (
    pack_frame_buffer,
    pack_indices_byte,
    pack_indices_packed,
    unpack_frame_buffer,
    unpack_indices_byte,
    unpack_indices_packed,
)
from processing.color import build_palette_lab, nearest_palette_indices, rgb_to_lab_cie
from processing.dither import indices_to_preview_rgb, quantize_to_palette
from processing.pipeline import process_image_to_binary, run_daily_processing
from processing.resize import resize_cover, resize_contain, resize_for_display, resize_stretch
from processing.sources import find_latest_source_image
from processing.types import DitherMethod, PackMode, ResizeMode

__all__ = [
    "DitherMethod",
    "PackMode",
    "ResizeMode",
    "build_palette_lab",
    "find_latest_source_image",
    "indices_to_preview_rgb",
    "nearest_palette_indices",
    "pack_frame_buffer",
    "pack_indices_byte",
    "pack_indices_packed",
    "process_image_to_binary",
    "quantize_to_palette",
    "resize_cover",
    "resize_contain",
    "resize_for_display",
    "resize_stretch",
    "rgb_to_lab_cie",
    "run_daily_processing",
    "unpack_frame_buffer",
    "unpack_indices_byte",
    "unpack_indices_packed",
]

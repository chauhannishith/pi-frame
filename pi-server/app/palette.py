"""
6-color palette for the 7.3-inch e-ink display.

Index order matches common Waveshare 6-color panel conventions.
"""

import numpy as np

# RGB values (0-255)
EINK_PALETTE_RGB = np.array(
    [
        [0, 0, 0],          # 0 — black
        [255, 255, 255],    # 1 — white
        [0, 255, 0],        # 2 — green
        [0, 0, 255],        # 3 — blue
        [255, 0, 0],        # 4 — red
        [255, 255, 0],      # 5 — yellow
    ],
    dtype=np.float32,
)

PALETTE_NAMES = ("black", "white", "green", "blue", "red", "yellow")

NUM_COLORS = len(EINK_PALETTE_RGB)

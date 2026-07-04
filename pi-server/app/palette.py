"""
6-color palette for the 7.3-inch e-ink display (WVSH0103).

Index order: black, white, blue, green, red, yellow.
"""

import numpy as np

EINK_PALETTE_RGB = np.array(
    [
        [0, 0, 0],          # 0 — black
        [255, 255, 255],    # 1 — white
        [0, 0, 255],        # 2 — blue
        [0, 255, 0],        # 3 — green
        [255, 0, 0],        # 4 — red
        [255, 255, 0],      # 5 — yellow
    ],
    dtype=np.float32,
)

PALETTE_NAMES = ("black", "white", "blue", "green", "red", "yellow")

NUM_COLORS = len(EINK_PALETTE_RGB)

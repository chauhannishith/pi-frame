import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

APP_DIR = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(APP_DIR))


@pytest.fixture
def solid_red_image() -> Image.Image:
    return Image.new("RGB", (100, 80), (255, 0, 0))


@pytest.fixture
def gradient_image() -> Image.Image:
    arr = np.zeros((60, 120, 3), dtype=np.uint8)
    for x in range(120):
        arr[:, x] = [x * 2, 64, 255 - x * 2]
    return Image.fromarray(arr, mode="RGB")


@pytest.fixture
def tiny_checker_image() -> Image.Image:
    img = Image.new("RGB", (4, 4))
    pixels = [
        (0, 0, 0), (255, 255, 255), (0, 0, 0), (255, 255, 255),
        (255, 255, 255), (0, 0, 0), (255, 255, 255), (0, 0, 0),
        (0, 0, 0), (255, 255, 255), (0, 0, 0), (255, 255, 255),
        (255, 255, 255), (0, 0, 0), (255, 255, 255), (0, 0, 0),
    ]
    img.putdata(pixels)
    return img

import numpy as np
from PIL import Image

from processing.focal_crop import (
    compute_focal_crop_box,
    compute_vertical_crop_top,
    cover_scale_size,
    resize_cover_focal,
)
from processing.resize import resize_for_display
from processing.types import ResizeMode


class TestCoverScaleSize:
    def test_wide_landscape_fills_height(self):
        # 16:9 source is wider than 800:480 frame — height binds at 480
        new_w, new_h, _ = cover_scale_size(1600, 900, 800, 480)
        assert new_h == 480
        assert new_w >= 800

    def test_tall_portrait_fills_width(self):
        # 9:16 source is taller than frame — width binds at 800
        new_w, new_h, _ = cover_scale_size(900, 1600, 800, 480)
        assert new_w == 800
        assert new_h >= 480


class TestVerticalCropTop:
    def test_centers_on_focal_y(self):
        # scaled_h=1000, crop_h=480, face at y=400 -> top=160
        assert compute_vertical_crop_top(1000, 480, focal_y=400.0) == 160

    def test_clamps_to_top(self):
        assert compute_vertical_crop_top(1000, 480, focal_y=50.0) == 0

    def test_clamps_to_bottom(self):
        assert compute_vertical_crop_top(1000, 480, focal_y=980.0) == 520

    def test_fallback_uses_top_weighted_offset(self):
        # max_top=520, 35% -> 182
        assert compute_vertical_crop_top(1000, 480, focal_y=None, fallback_ratio=0.35) == 182


class TestFocalCropBox:
    def test_horizontal_centering(self):
        box = compute_focal_crop_box(1200, 900, 800, 480, face_centers_y=[450.0])
        left, top, right, bottom = box
        assert right - left == 800
        assert bottom - top == 480
        assert left == 200

    def test_no_face_uses_fallback(self):
        box = compute_focal_crop_box(1200, 900, 800, 480, face_centers_y=[])
        assert box[1] == compute_vertical_crop_top(900, 480, focal_y=None)


class TestResizeCoverFocal:
    def test_output_dimensions(self):
        src = Image.new("RGB", (2000, 1500), (100, 120, 140))
        result = resize_cover_focal(src, 800, 480)
        assert result.size == (800, 480)

    def test_cover_mode_uses_focal_crop(self):
        src = Image.new("RGB", (1200, 800), (80, 90, 100))
        result = resize_for_display(src, 800, 480, mode=ResizeMode.COVER)
        assert result.size == (800, 480)

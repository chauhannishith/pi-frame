import numpy as np
from PIL import Image

from processing.focal_crop import (
    adaptive_pad_color,
    average_luminance,
    compute_horizontal_crop_left,
    compute_paste_x,
    compute_vertical_crop_top,
    resize_smart_focal,
    scale_to_height,
)
from processing.resize import resize_for_display
from processing.types import ResizeMode


class TestScaleToHeight:
    def test_landscape_scales_height_to_target(self):
        new_w, new_h, _ = scale_to_height(1600, 900, 480)
        assert new_h == 480
        assert new_w == 853

    def test_portrait_scales_height_to_target(self):
        new_w, new_h, _ = scale_to_height(900, 1600, 480)
        assert new_h == 480
        assert new_w == 270


class TestAdaptivePadColor:
    def test_bright_image_gets_white_pad(self):
        rgb = np.full((10, 10, 3), 200, dtype=np.uint8)
        assert adaptive_pad_color(rgb) == (255, 255, 255)

    def test_dark_image_gets_black_pad(self):
        rgb = np.full((10, 10, 3), 40, dtype=np.uint8)
        assert adaptive_pad_color(rgb) == (0, 0, 0)

    def test_luminance_uses_perceptual_weights(self):
        rgb = np.array([[[127, 127, 127]]], dtype=np.uint8)
        assert average_luminance(rgb) == 127.0


class TestHorizontalCropLeft:
    def test_centers_on_focal_x(self):
        assert compute_horizontal_crop_left(1200, 800, focal_x=600.0) == 200

    def test_clamps_to_left_edge(self):
        assert compute_horizontal_crop_left(1200, 800, focal_x=100.0) == 0

    def test_clamps_to_right_edge(self):
        assert compute_horizontal_crop_left(1200, 800, focal_x=1150.0) == 400


class TestVerticalCropTop:
    def test_centers_on_focal_y(self):
        assert compute_vertical_crop_top(1000, 480, focal_y=400.0) == 160

    def test_fallback_uses_top_weighted_offset(self):
        assert compute_vertical_crop_top(1000, 480, focal_y=None, fallback_ratio=0.35) == 182


class TestPasteX:
    def test_centers_content_without_face(self):
        assert compute_paste_x(800, 400, focal_x=None) == 200

    def test_centers_face_on_canvas(self):
        # face at x=200 in 400px-wide content → paste at 200 so face lands at canvas center
        assert compute_paste_x(800, 400, focal_x=200.0) == 200

    def test_clamps_when_face_past_left_edge(self):
        assert compute_paste_x(800, 400, focal_x=500.0) == 0


class TestResizeSmartFocal:
    def test_wide_landscape_crops_to_exact_frame(self):
        src = Image.new("RGB", (1600, 900), (100, 120, 140))
        result = resize_smart_focal(src, 800, 480)
        assert result.size == (800, 480)

    def test_portrait_pads_to_exact_frame(self):
        src = Image.new("RGB", (600, 1200), (200, 200, 200))
        result = resize_smart_focal(src, 800, 480)
        assert result.size == (800, 480)
        assert result.getpixel((0, 240)) == (255, 255, 255)
        assert result.getpixel((799, 240)) == (255, 255, 255)

    def test_portrait_dark_image_gets_black_pad(self):
        src = Image.new("RGB", (600, 1200), (20, 25, 30))
        result = resize_smart_focal(src, 800, 480)
        assert result.getpixel((0, 240)) == (0, 0, 0)

    def test_square_uses_portrait_path(self):
        src = Image.new("RGB", (1000, 1000), (180, 180, 180))
        result = resize_smart_focal(src, 800, 480)
        assert result.size == (800, 480)
        assert result.getpixel((0, 0)) == (255, 255, 255)

    def test_cover_mode_uses_smart_focal(self):
        src = Image.new("RGB", (1200, 800), (80, 90, 100))
        result = resize_for_display(src, 800, 480, mode=ResizeMode.COVER)
        assert result.size == (800, 480)

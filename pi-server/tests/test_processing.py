import numpy as np
import pytest
from PIL import Image

from palette import EINK_PALETTE_RGB, NUM_COLORS
from processing import (
    ResizeMode,
    build_palette_lab,
    find_latest_source_image,
    indices_to_preview_rgb,
    nearest_palette_indices,
    pack_frame_buffer,
    process_image_to_binary,
    quantize_to_palette,
    resize_for_display,
    unpack_frame_buffer,
)


class TestResizeForDisplay:
    def test_cover_crop_to_exact_dimensions(self, solid_red_image):
        result = resize_for_display(solid_red_image, 32, 24, mode=ResizeMode.COVER)
        assert result.size == (32, 24)

    def test_contain_letterboxes(self, solid_red_image):
        result = resize_for_display(solid_red_image, 40, 40, mode=ResizeMode.CONTAIN)
        assert result.size == (40, 40)
        corners = [result.getpixel((0, 0)), result.getpixel((39, 39))]
        assert all(p == (255, 255, 255) for p in corners)

    def test_stretch_ignores_aspect_ratio(self):
        src = Image.new("RGB", (200, 50), (0, 128, 255))
        result = resize_for_display(src, 10, 10, mode=ResizeMode.STRETCH)
        assert result.size == (10, 10)


class TestPaletteQuantization:
    def test_build_palette_lab_has_six_entries(self):
        lab = build_palette_lab()
        assert lab.shape == (NUM_COLORS, 3)

    def test_pure_red_maps_to_red_index(self, solid_red_image):
        resized = resize_for_display(solid_red_image, 16, 16)
        indices = quantize_to_palette(resized, method="nearest")
        assert int(np.median(indices)) == 4  # red

    def test_pure_white_maps_to_white_index(self):
        img = Image.new("RGB", (8, 8), (255, 255, 255))
        indices = quantize_to_palette(img, method="nearest")
        assert np.all(indices == 1)

    def test_floyd_steinberg_differs_from_nearest_on_gradient(self, gradient_image):
        resized = resize_for_display(gradient_image, 48, 24)
        nearest = quantize_to_palette(resized, method="nearest")
        dithered = quantize_to_palette(resized, method="floyd_steinberg")
        assert not np.array_equal(nearest, dithered)
        assert dithered.max() < NUM_COLORS

    def test_atkinson_produces_valid_indices(self, gradient_image):
        resized = resize_for_display(gradient_image, 32, 16)
        indices = quantize_to_palette(resized, method="atkinson")
        assert indices.shape == (16, 32)
        assert indices.max() < NUM_COLORS


class TestNearestPaletteIndices:
    def test_cie_lab_distance_picks_closest_swatch(self):
        palette_lab = build_palette_lab()
        white_rgb = np.tile(EINK_PALETTE_RGB[1], (2, 2, 1))
        indices = nearest_palette_indices(white_rgb, EINK_PALETTE_RGB, palette_lab)
        assert np.all(indices == 1)

    def test_pure_red_picks_red_swatch(self):
        palette_lab = build_palette_lab()
        red_rgb = np.full((2, 2, 3), 255.0, dtype=np.float32)
        red_rgb[..., 1:] = 0.0
        indices = nearest_palette_indices(red_rgb, EINK_PALETTE_RGB, palette_lab)
        assert np.all(indices == 4)


class TestBinaryPacking:
    @pytest.mark.parametrize("width,height", [(4, 4), (10, 7), (32, 24)])
    def test_byte_mode_roundtrip(self, width, height):
        rng = np.random.default_rng(42)
        indices = rng.integers(0, NUM_COLORS, size=(height, width), dtype=np.uint8)
        packed = pack_frame_buffer(indices, mode="byte")
        restored = unpack_frame_buffer(packed, width, height, mode="byte")
        assert np.array_equal(indices, restored)
        assert len(packed) == width * height

    @pytest.mark.parametrize("width,height", [(8, 8), (10, 7), (32, 24)])
    def test_packed_mode_roundtrip(self, width, height):
        rng = np.random.default_rng(7)
        indices = rng.integers(0, NUM_COLORS, size=(height, width), dtype=np.uint8)
        packed = pack_frame_buffer(indices, mode="packed")
        restored = unpack_frame_buffer(packed, width, height, mode="packed")
        assert np.array_equal(indices, restored)
        padded_pixels = ((width * height + 7) // 8) * 8
        assert len(packed) == padded_pixels * 3 // 8

    def test_byte_mode_rejects_out_of_range_index(self):
        bad = np.array([[6]], dtype=np.uint8)
        with pytest.raises(ValueError, match="out of range"):
            pack_frame_buffer(bad, mode="byte")


class TestProcessImageToBinary:
    def test_writes_file_with_expected_byte_size(self, solid_red_image, tmp_path):
        src = tmp_path / "input.png"
        out = tmp_path / "frame.bin"
        solid_red_image.save(src)

        process_image_to_binary(
            src,
            out,
            width=16,
            height=12,
            dither_method="nearest",
            pack_mode="byte",
        )

        assert out.is_file()
        assert out.stat().st_size == 16 * 12

    def test_preview_rgb_uses_palette_colors(self, tiny_checker_image):
        resized = resize_for_display(tiny_checker_image, 4, 4)
        indices = quantize_to_palette(resized, method="nearest")
        preview = indices_to_preview_rgb(indices)
        unique = {tuple(c) for c in preview.reshape(-1, 3)}
        for color in unique:
            assert any(np.array_equal(color, sw.astype(np.uint8)) for sw in EINK_PALETTE_RGB)

    def test_missing_source_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            process_image_to_binary(tmp_path / "nope.jpg", tmp_path / "out.bin", 8, 8)


class TestFindLatestSourceImage:
    def test_returns_newest_supported_file(self, tmp_path):
        older = tmp_path / "old.png"
        newer = tmp_path / "new.jpg"
        Image.new("RGB", (4, 4), (0, 0, 0)).save(older)
        Image.new("RGB", (4, 4), (255, 0, 0)).save(newer)

        import os
        import time

        os.utime(older, (time.time() - 100, time.time() - 100))
        os.utime(newer, (time.time(), time.time()))

        assert find_latest_source_image(tmp_path) == newer

    def test_returns_none_for_empty_directory(self, tmp_path):
        assert find_latest_source_image(tmp_path) is None

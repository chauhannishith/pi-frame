import numpy as np

from processing.frame_orientation import (
    normalize_orientation,
    orient_indices,
    processing_dimensions,
)


class TestFrameOrientation:
    def test_normalize_defaults_to_landscape(self):
        assert normalize_orientation(None) == "landscape"
        assert normalize_orientation("invalid") == "landscape"

    def test_processing_dimensions_swap_for_portrait(self):
        assert processing_dimensions("landscape") == (800, 480)
        assert processing_dimensions("portrait") == (480, 800)

    def test_orient_indices_rotates_portrait_to_native(self):
        indices = np.arange(480 * 800, dtype=np.uint8).reshape(800, 480)
        out = orient_indices(indices, "portrait")
        assert out.shape == (480, 800)

    def test_orient_indices_unchanged_for_landscape(self):
        indices = np.zeros((480, 800), dtype=np.uint8)
        out = orient_indices(indices, "landscape")
        assert out.shape == (480, 800)
        assert np.array_equal(out, indices)

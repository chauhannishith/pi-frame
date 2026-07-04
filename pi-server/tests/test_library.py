import numpy as np
import pytest
from PIL import Image

from library import (
    add_to_library,
    delete_from_library,
    list_library_images,
    next_image_for_processing,
)


@pytest.fixture
def library_dir(tmp_path):
    return tmp_path / "source_images"


class TestLibraryRotation:
    def test_next_image_cycles_through_library(self, library_dir):
        library_dir.mkdir()
        for name, color in [("a.png", (255, 0, 0)), ("b.png", (0, 255, 0)), ("c.png", (0, 0, 255))]:
            Image.new("RGB", (4, 4), color).save(library_dir / name)

        state_path = library_dir / "state.json"
        first = next_image_for_processing(library_dir, state_path)
        second = next_image_for_processing(library_dir, state_path)
        third = next_image_for_processing(library_dir, state_path)
        fourth = next_image_for_processing(library_dir, state_path)

        assert first.name == "a.png"
        assert second.name == "b.png"
        assert third.name == "c.png"
        assert fourth.name == "a.png"

    def test_empty_library_returns_none(self, library_dir):
        assert next_image_for_processing(library_dir) is None

    def test_delete_adjusts_rotation(self, library_dir):
        library_dir.mkdir()
        Image.new("RGB", (4, 4), (255, 0, 0)).save(library_dir / "a.png")
        Image.new("RGB", (4, 4), (0, 255, 0)).save(library_dir / "b.png")

        state_path = library_dir / "state.json"
        next_image_for_processing(library_dir, state_path)
        delete_from_library(library_dir, "a.png", state_path)

        images = list_library_images(library_dir)
        assert len(images) == 1
        assert images[0].name == "b.png"

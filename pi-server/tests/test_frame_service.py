from unittest.mock import patch

import pytest
from PIL import Image

from frame_service import (
    format_quick_action_message,
    generate_preview,
    reprocess_active_output,
    toggle_frame_dither,
    toggle_frame_orientation,
)
from settings_store import (
    get_default_dither_method,
    get_frame_orientation,
    record_preview,
)


def _seed_library_image(source_dir, name: str = "photo.jpg", size: tuple[int, int] = (400, 300)) -> str:
    Image.new("RGB", size, (120, 80, 60)).save(source_dir / name, "JPEG")
    return name


class TestFrameServiceQuickActions:
    def test_format_quick_action_message_with_source(self):
        msg = format_quick_action_message("Portrait", "photo.jpg")
        assert "Portrait" in msg
        assert "photo.jpg" in msg
        assert "wake button" in msg

    def test_format_quick_action_message_without_source(self):
        assert format_quick_action_message("Frame orientation set to Portrait.", None) == (
            "Frame orientation set to Portrait."
        )

    def test_toggle_orientation_without_source_updates_setting_only(self, app_paths):
        assert get_frame_orientation() == "landscape"
        new_orientation, source = toggle_frame_orientation()
        assert new_orientation == "portrait"
        assert source is None
        assert get_frame_orientation() == "portrait"
        assert not app_paths["frame_path"].is_file()

    def test_toggle_dither_without_source_updates_default_only(self, app_paths):
        assert get_default_dither_method() == "floyd_steinberg"
        new_method, source = toggle_frame_dither()
        assert new_method == "atkinson"
        assert source is None
        assert get_default_dither_method() == "atkinson"

    def test_reprocess_active_output_returns_none_without_source(self, app_paths):
        assert reprocess_active_output() is None

    @patch("frame_service.process_specific_image")
    def test_reprocess_active_output_uses_library_original(
        self,
        mock_process,
        app_paths,
    ):
        name = _seed_library_image(app_paths["source_dir"])
        record_preview(name, "floyd_steinberg", "landscape")

        result = reprocess_active_output(dither_method="atkinson", frame_orientation="portrait")

        assert result == name
        mock_process.assert_called_once()
        called_path, = mock_process.call_args.args[:1]
        assert called_path.name == name
        assert called_path.parent == app_paths["source_dir"]
        assert mock_process.call_args.kwargs["dither_method"] == "atkinson"
        assert mock_process.call_args.kwargs["frame_orientation"] == "portrait"

    @patch("frame_service.process_specific_image")
    def test_toggle_orientation_reprocesses_active_source(self, mock_process, app_paths):
        name = _seed_library_image(app_paths["source_dir"])
        record_preview(name, "floyd_steinberg", "landscape")

        new_orientation, source = toggle_frame_orientation()

        assert new_orientation == "portrait"
        assert source == name
        assert get_frame_orientation() == "portrait"
        mock_process.assert_called_once()

    @patch("frame_service.process_specific_image")
    def test_toggle_dither_reprocesses_active_source(self, mock_process, app_paths):
        name = _seed_library_image(app_paths["source_dir"])
        record_preview(name, "floyd_steinberg", "landscape")

        new_method, source = toggle_frame_dither()

        assert new_method == "atkinson"
        assert source == name
        assert get_default_dither_method() == "atkinson"
        mock_process.assert_called_once()

    def test_generate_preview_writes_preview_from_original(self, app_paths):
        name = _seed_library_image(app_paths["source_dir"])
        path = app_paths["source_dir"] / name

        generate_preview(path, dither_method="floyd_steinberg", frame_orientation="landscape")

        assert app_paths["preview_path"].is_file()
        assert not app_paths["frame_path"].is_file()

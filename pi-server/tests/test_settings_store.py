from datetime import datetime, timezone

import pytest

from settings_store import (
    format_frame_output_status,
    get_active_dither_method,
    get_default_dither_method,
    get_frame_orientation,
    record_preview,
    set_default_dither_method,
    set_frame_orientation,
)


class TestSettingsStore:
    def test_default_dither_method(self, app_paths):
        assert get_default_dither_method() == "floyd_steinberg"

    def test_set_default_dither_method(self, app_paths):
        set_default_dither_method("atkinson")
        assert get_default_dither_method() == "atkinson"

    def test_set_invalid_dither_raises(self, app_paths):
        with pytest.raises(ValueError):
            set_default_dither_method("invalid")

    def test_get_active_dither_falls_back_to_default(self, app_paths):
        set_default_dither_method("atkinson")
        assert get_active_dither_method() == "atkinson"

    def test_get_active_dither_uses_last_preview(self, app_paths):
        set_default_dither_method("floyd_steinberg")
        record_preview("photo.jpg", "atkinson", "landscape")
        assert get_active_dither_method() == "atkinson"

    def test_frame_orientation_defaults_and_persists(self, app_paths):
        assert get_frame_orientation() == "landscape"
        set_frame_orientation("portrait")
        assert get_frame_orientation() == "portrait"

    def test_record_preview_persists_source_and_dither(self, app_paths):
        record_preview("vacation.jpg", "atkinson", "portrait")
        assert get_active_dither_method() == "atkinson"
        assert get_frame_orientation() == "portrait"

        status, filename, _time = format_frame_output_status(None, None)
        assert status == "Ready to push"
        assert filename == "vacation.jpg"

    def test_format_frame_output_status_on_frame(self, app_paths):
        record_preview("vacation.jpg", "floyd_steinberg", "landscape")
        status, filename, time_label = format_frame_output_status("vacation.jpg", None)
        assert status == "On frame"
        assert filename == "vacation.jpg"
        assert time_label == "just now"

    def test_format_frame_output_status_ready_to_push(self, app_paths):
        record_preview("draft.jpg", "floyd_steinberg", "landscape")
        status, filename, _time = format_frame_output_status("other.jpg", None)
        assert status == "Ready to push"
        assert filename == "draft.jpg"

    def test_format_frame_output_status_no_preview(self, app_paths):
        status, filename, time_label = format_frame_output_status(None, None)
        assert status == "No preview yet"
        assert filename == "—"
        assert time_label == "—"

    def test_format_frame_output_status_on_frame_without_preview_record(self, app_paths):
        processed_at = datetime.now(timezone.utc).isoformat()
        status, filename, time_label = format_frame_output_status("old.jpg", processed_at)
        assert status == "On frame"
        assert filename == "old.jpg"
        assert time_label == "just now"

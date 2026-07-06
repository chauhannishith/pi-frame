import pytest

from ui.dither_controls import dither_method_label, dither_toggle_html
from ui.layout import gallery_sidebar
from ui.orientation_controls import orientation_toggle_html


class TestOrientationControls:
    def test_standalone_toggle_shows_current_and_switch_label(self):
        html = orientation_toggle_html("landscape", action="/gallery/orientation")
        assert "Orientation:" in html
        assert "Landscape" in html
        assert 'action="/gallery/orientation"' in html
        assert "Switch to Portrait" in html

    def test_form_id_toggle_submits_orientation_action(self):
        html = orientation_toggle_html("portrait", form_id="preview-form")
        assert 'form="preview-form"' in html
        assert 'name="action" value="orientation"' in html
        assert "Switch to Landscape" in html

    def test_requires_action_or_form_id(self):
        with pytest.raises(ValueError):
            orientation_toggle_html("landscape")


class TestDitherControls:
    def test_dither_method_label(self):
        assert dither_method_label("floyd_steinberg") == "Floyd-Steinberg"
        assert dither_method_label("atkinson") == "Atkinson"

    def test_dither_toggle_shows_other_method(self):
        html = dither_toggle_html("floyd_steinberg", action="/gallery/dither")
        assert "Dither:" in html
        assert "Floyd-Steinberg" in html
        assert 'action="/gallery/dither"' in html
        assert "Switch to Atkinson" in html

    def test_dither_toggle_from_atkinson(self):
        html = dither_toggle_html("atkinson", action="/settings/dither", full_width=True)
        assert "Switch to Floyd-Steinberg" in html
        assert "width:100%" in html


class TestGallerySidebar:
    def test_sidebar_includes_quick_action_forms(self):
        html = gallery_sidebar(
            count=2,
            last_source="a.jpg",
            next_name="b.jpg",
            frame_status="Ready to push",
            frame_filename="a.jpg",
            frame_time="just now",
            frame_orientation="landscape",
            dither_method="floyd_steinberg",
        )
        assert 'class="quick-actions"' in html
        assert 'action="/gallery/dither"' in html
        assert 'action="/gallery/orientation"' in html
        assert "Switch to Atkinson" in html
        assert "Switch to Portrait" in html

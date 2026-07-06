from unittest.mock import patch

from settings_store import get_default_dither_method, get_frame_orientation


class TestSettingsRoutes:
    def test_settings_page_renders_dither_form_and_mobile_quick_actions(self, flask_client):
        response = flask_client.get("/settings")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "Default dither method" in body
        assert 'name="default_dither_method"' in body
        assert "settings-quick-actions-mobile" in body
        assert 'action="/settings/dither"' in body
        assert 'action="/settings/orientation"' in body

    def test_settings_save_persists_dither_default(self, flask_client, app_paths):
        response = flask_client.post(
            "/settings",
            data={"default_dither_method": "atkinson"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Settings saved" in response.data
        assert get_default_dither_method() == "atkinson"

    @patch("settings_routes.toggle_frame_orientation")
    def test_settings_orientation_post(self, mock_toggle, flask_client):
        mock_toggle.return_value = ("portrait", "photo.jpg")
        response = flask_client.post("/settings/orientation", follow_redirects=True)
        assert response.status_code == 200
        assert b"Portrait" in response.data
        assert b"photo.jpg" in response.data
        mock_toggle.assert_called_once()

    @patch("settings_routes.toggle_frame_dither")
    def test_settings_dither_post(self, mock_toggle, flask_client):
        mock_toggle.return_value = ("atkinson", "photo.jpg")
        response = flask_client.post("/settings/dither", follow_redirects=True)
        assert response.status_code == 200
        assert b"Atkinson" in response.data
        assert b"photo.jpg" in response.data
        mock_toggle.assert_called_once()

    def test_settings_dither_without_active_source(self, flask_client, app_paths):
        response = flask_client.post("/settings/dither", follow_redirects=True)
        assert response.status_code == 200
        assert b"Default dither method set to Atkinson" in response.data
        assert get_default_dither_method() == "atkinson"
        assert not app_paths["frame_path"].is_file()

    def test_settings_orientation_without_active_source(self, flask_client):
        response = flask_client.post("/settings/orientation", follow_redirects=True)
        assert response.status_code == 200
        assert b"Frame orientation set to Portrait" in response.data
        assert get_frame_orientation() == "portrait"

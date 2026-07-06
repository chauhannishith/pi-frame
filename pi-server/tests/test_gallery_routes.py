from unittest.mock import patch

from PIL import Image

from settings_store import get_frame_orientation, record_preview


def _seed_library_image(source_dir, name: str = "photo.jpg") -> str:
    Image.new("RGB", (400, 300), (120, 80, 60)).save(source_dir / name, "JPEG")
    return name


class TestGalleryRoutes:
    def test_gallery_index_renders_quick_actions(self, flask_client):
        response = flask_client.get("/gallery")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "pi-frame" in body
        assert 'action="/gallery/dither"' in body
        assert 'action="/gallery/orientation"' in body
        assert 'class="quick-actions"' in body

    def test_gallery_index_lists_library_images(self, flask_client, app_paths):
        _seed_library_image(app_paths["source_dir"], "sunset.jpg")
        response = flask_client.get("/gallery")
        body = response.get_data(as_text=True)
        assert "sunset.jpg" in body

    @patch("gallery_routes.toggle_frame_orientation")
    def test_gallery_orientation_post_redirects_with_message(self, mock_toggle, flask_client):
        mock_toggle.return_value = ("portrait", "photo.jpg")
        response = flask_client.post("/gallery/orientation", follow_redirects=True)
        assert response.status_code == 200
        assert b"Portrait" in response.data
        assert b"photo.jpg" in response.data
        mock_toggle.assert_called_once()

    @patch("gallery_routes.toggle_frame_dither")
    def test_gallery_dither_post_redirects_with_message(self, mock_toggle, flask_client):
        mock_toggle.return_value = ("atkinson", "photo.jpg")
        response = flask_client.post("/gallery/dither", follow_redirects=True)
        assert response.status_code == 200
        assert b"Atkinson" in response.data
        assert b"photo.jpg" in response.data
        mock_toggle.assert_called_once()

    @patch("gallery_routes.generate_preview")
    def test_gallery_view_preview_post(self, mock_preview, flask_client, app_paths):
        name = _seed_library_image(app_paths["source_dir"])
        mock_preview.return_value = name
        response = flask_client.post(
            f"/gallery/view/{name}",
            data={"action": "preview", "dither_method": "atkinson"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        mock_preview.assert_called_once()
        called_path = mock_preview.call_args.args[0]
        assert called_path.name == name

    @patch("gallery_routes.process_specific_image")
    def test_gallery_view_push_post(self, mock_push, flask_client, app_paths):
        name = _seed_library_image(app_paths["source_dir"])
        mock_push.return_value = name
        response = flask_client.post(
            f"/gallery/view/{name}",
            data={"action": "push", "dither_method": "floyd_steinberg"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Pushed to frame" in response.data
        mock_push.assert_called_once()

    @patch("gallery_routes.generate_preview")
    def test_gallery_view_orientation_toggle_regenerates_preview(
        self,
        mock_preview,
        flask_client,
        app_paths,
    ):
        name = _seed_library_image(app_paths["source_dir"])
        mock_preview.return_value = name
        response = flask_client.post(
            f"/gallery/view/{name}",
            data={"action": "orientation", "dither_method": "floyd_steinberg"},
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert get_frame_orientation() == "portrait"
        mock_preview.assert_called_once()
        assert mock_preview.call_args.kwargs["frame_orientation"] == "portrait"

    def test_gallery_view_unknown_file_returns_404(self, flask_client):
        response = flask_client.get("/gallery/view/missing.jpg")
        assert response.status_code == 404

    @patch("gallery_routes.change_frame")
    def test_gallery_change_post(self, mock_change, flask_client):
        mock_change.return_value = "photo.jpg"
        response = flask_client.post("/gallery/change", follow_redirects=True)
        assert response.status_code == 200
        assert b"Frame changed to photo.jpg" in response.data

    def test_gallery_orientation_without_active_source_sets_setting(self, flask_client, app_paths):
        response = flask_client.post("/gallery/orientation", follow_redirects=True)
        assert response.status_code == 200
        assert b"Frame orientation set to Portrait" in response.data
        assert get_frame_orientation() == "portrait"
        assert not app_paths["frame_path"].is_file()

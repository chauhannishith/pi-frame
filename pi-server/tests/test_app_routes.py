class TestAppRoutes:
    def test_root_redirects_to_gallery(self, flask_client):
        response = flask_client.get("/")
        assert response.status_code == 302
        assert response.headers["Location"].endswith("/gallery")

    def test_legacy_upload_redirects_to_gallery(self, flask_client):
        response = flask_client.get("/upload")
        assert response.status_code == 302
        assert "/gallery" in response.headers["Location"]

    def test_preview_png_404_when_missing(self, flask_client):
        response = flask_client.get("/preview.png")
        assert response.status_code == 404

    def test_preview_png_served_when_present(self, flask_client, app_paths):
        app_paths["preview_path"].write_bytes(b"\x89PNG\r\n")
        response = flask_client.get("/preview.png")
        assert response.status_code == 200
        assert response.mimetype == "image/png"

    def test_latest_frame_404_when_missing(self, flask_client):
        response = flask_client.get("/get_latest_frame.bin")
        assert response.status_code == 404

    def test_latest_frame_served_when_present(self, flask_client, app_paths):
        app_paths["frame_path"].write_bytes(b"\x00\x01\x02")
        response = flask_client.get("/get_latest_frame.bin")
        assert response.status_code == 200
        assert response.mimetype == "application/octet-stream"
        assert response.data == b"\x00\x01\x02"

"""
Google Photos integration — OAuth 2.0 and photo download.
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_PHOTOS_SCOPES,
    GOOGLE_REDIRECT_URI,
    GOOGLE_TOKEN_PATH,
)

logger = logging.getLogger(__name__)

PHOTOS_API_BASE = "https://photoslibrary.googleapis.com/v1"


def is_google_photos_configured() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def _token_path(token_path: str | Path | None = None) -> Path:
    return Path(token_path or GOOGLE_TOKEN_PATH)


def _client_config() -> dict:
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def load_credentials(token_path: str | Path | None = None) -> Credentials | None:
    """Load stored OAuth credentials, refreshing if expired."""
    path = _token_path(token_path)
    if not path.is_file():
        return None

    creds = Credentials.from_authorized_user_file(str(path), GOOGLE_PHOTOS_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        save_credentials(creds, path)
    return creds if creds.valid else None


def save_credentials(creds: Credentials, token_path: str | Path | None = None) -> None:
    path = _token_path(token_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(creds.to_json())


def create_oauth_flow(state: str | None = None) -> Flow:
    """Build the Google OAuth consent flow."""
    flow = Flow.from_client_config(
        _client_config(),
        scopes=GOOGLE_PHOTOS_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    if state:
        flow.state = state
    return flow


def get_authorization_url(state: str) -> str:
    flow = create_oauth_flow(state=state)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code_for_credentials(code: str, state: str) -> Credentials:
    flow = create_oauth_flow(state=state)
    flow.fetch_token(code=code)
    creds = flow.credentials
    save_credentials(creds)
    return creds


def is_connected(token_path: str | Path | None = None) -> bool:
    return load_credentials(token_path) is not None


def _auth_headers(creds: Credentials) -> dict:
    return {"Authorization": f"Bearer {creds.token}"}


def _list_media_items(creds: Credentials, page_size: int = 100) -> list[dict]:
    """Fetch recent photos from the user's Google Photos library."""
    items: list[dict] = []
    page_token = None

    while len(items) < page_size:
        params = {"pageSize": min(100, page_size - len(items))}
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(
            f"{PHOTOS_API_BASE}/mediaItems",
            headers=_auth_headers(creds),
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        items.extend(data.get("mediaItems", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return items


def fetch_random_photo(
    destination_dir: str | Path,
    token_path: str | Path | None = None,
) -> Path:
    """
    Download a random recent photo from Google Photos into the library folder.

    Returns the saved file path.
    """
    creds = load_credentials(token_path)
    if creds is None:
        raise RuntimeError("Google Photos not connected — visit /google/connect first")

    items = _list_media_items(creds)
    photos = [
        item
        for item in items
        if item.get("mimeType", "").startswith("image/")
    ]
    if not photos:
        raise RuntimeError("No photos found in your Google Photos library")

    item = random.choice(photos)
    base_url = item["baseUrl"]
    download_url = f"{base_url}=d"
    filename = item.get("filename", "google_photo.jpg")
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png"}:
        suffix = ".jpg"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = Path(destination_dir) / f"google_{timestamp}_{stem}{suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)

    response = requests.get(download_url, timeout=60)
    response.raise_for_status()
    dest.write_bytes(response.content)

    logger.info("Downloaded Google Photo: %s", dest.name)
    return dest


def disconnect(token_path: str | Path | None = None) -> None:
    """Remove stored Google OAuth credentials."""
    path = _token_path(token_path)
    if path.is_file():
        path.unlink()
        logger.info("Google Photos disconnected")

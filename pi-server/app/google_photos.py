"""
Google Photos integration — OAuth 2.0 and photo download.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import random
import secrets
from datetime import datetime, timezone
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from config import (
    FLASK_SECRET_KEY,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_PHOTOS_SCOPES,
    GOOGLE_REDIRECT_URI,
    GOOGLE_TOKEN_PATH,
)

# Google OAuth library blocks http:// redirects unless this is set (localhost dev / LAN Pi)
if GOOGLE_REDIRECT_URI.startswith("http://"):
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

PICKER_API_BASE = "https://photospicker.googleapis.com/v1"
OAUTH_STATE_MAX_AGE_SECONDS = 600


def _oauth_state_signer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(FLASK_SECRET_KEY, salt="pi-frame-google-oauth")


def _pkce_s256_challenge(code_verifier: str) -> str:
    """PKCE S256 code_challenge derived from the verifier (auth URL only)."""
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _load_oauth_state(state: str) -> dict:
    """Verify and decode signed OAuth state payload."""
    payload = _oauth_state_signer().loads(state, max_age=OAUTH_STATE_MAX_AGE_SECONDS)
    if not isinstance(payload, dict):
        raise TypeError("state payload must be a dict")
    return payload


def create_oauth_state() -> str:
    """Return a signed state token embedding the PKCE code_verifier."""
    code_verifier = secrets.token_urlsafe(48)
    return _oauth_state_signer().dumps({
        "nonce": secrets.token_urlsafe(16),
        "cv": code_verifier,
    })


def verify_oauth_state(state: str) -> bool:
    """Verify state returned by Google matches our signed token."""
    return oauth_state_error(state) is None


def oauth_state_error(state: str | None) -> str | None:
    """Return a human-readable reason when state verification fails."""
    if not state:
        return "no state parameter in callback URL"
    try:
        _load_oauth_state(state)
        return None
    except SignatureExpired:
        return "state token expired (took longer than 10 minutes)"
    except BadSignature:
        return "state signature invalid — check FLASK_SECRET_KEY is stable in .env"
    except TypeError:
        return "state token malformed"


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
    payload = _load_oauth_state(state)
    code_verifier = payload.get("cv")
    if not code_verifier:
        raise RuntimeError("OAuth state missing PKCE verifier — click Connect again")

    flow = create_oauth_flow(state=state)
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        state=state,
        code_challenge=_pkce_s256_challenge(code_verifier),
        code_challenge_method="S256",
    )
    return auth_url


def exchange_code_for_credentials(
    code: str,
    state: str,
    authorization_response: str | None = None,
) -> Credentials:
    payload = _load_oauth_state(state)
    code_verifier = payload.get("cv")
    if not code_verifier:
        raise RuntimeError("OAuth state missing PKCE verifier — click Connect again")

    flow = create_oauth_flow(state=state)
    flow.oauth2session._code_verifier = code_verifier
    try:
        if authorization_response:
            flow.fetch_token(
                authorization_response=authorization_response,
                code_verifier=code_verifier,
            )
        else:
            flow.fetch_token(
                code=code,
                redirect_uri=GOOGLE_REDIRECT_URI,
                code_verifier=code_verifier,
            )
    except Exception as exc:
        logger.exception("Google token exchange failed: %s", exc)
        raise RuntimeError(str(exc)) from exc
    creds = flow.credentials
    save_credentials(creds)
    return creds


def is_connected(token_path: str | Path | None = None) -> bool:
    return load_credentials(token_path) is not None


def _auth_headers(creds: Credentials) -> dict:
    return {"Authorization": f"Bearer {creds.token}"}


def _session_id_from_response(session: dict) -> str:
    session_id = session.get("id")
    if session_id:
        return str(session_id)

    name = session.get("name", "")
    prefix = "sessions/"
    if name.startswith(prefix):
        return name[len(prefix):]
    return name


def _raise_api_error(response: requests.Response, action: str) -> None:
    detail = response.text.strip()
    try:
        detail = response.json().get("error", {}).get("message", detail)
    except Exception:
        pass
    raise RuntimeError(f"{action} failed ({response.status_code}): {detail}")


def create_picker_session(creds: Credentials) -> dict:
    """Start a Google Photos Picker session; returns session resource."""
    response = requests.post(
        f"{PICKER_API_BASE}/sessions",
        headers=_auth_headers(creds),
        json={},
        timeout=30,
    )
    if not response.ok:
        _raise_api_error(response, "Create picker session")
    return response.json()


def get_picker_session(creds: Credentials, session_id: str) -> dict:
    response = requests.get(
        f"{PICKER_API_BASE}/sessions/{session_id}",
        headers=_auth_headers(creds),
        timeout=30,
    )
    if not response.ok:
        _raise_api_error(response, "Get picker session")
    return response.json()


def list_picked_media_items(creds: Credentials, session_id: str) -> list[dict]:
    response = requests.get(
        f"{PICKER_API_BASE}/mediaItems",
        headers=_auth_headers(creds),
        params={"sessionId": session_id},
        timeout=30,
    )
    if not response.ok:
        _raise_api_error(response, "List picked media items")
    data = response.json()
    return data.get("mediaItems", data.get("pickedMediaItems", []))


def delete_picker_session(creds: Credentials, session_id: str) -> None:
    response = requests.delete(
        f"{PICKER_API_BASE}/sessions/{session_id}",
        headers=_auth_headers(creds),
        timeout=30,
    )
    if response.status_code not in (200, 404):
        logger.warning("Picker session delete returned %s", response.status_code)


def _download_picked_item(creds: Credentials, item: dict, destination: Path) -> None:
    media_file = item.get("mediaFile") or item
    base_url = media_file.get("baseUrl")
    if not base_url:
        raise RuntimeError("Picked item has no download URL")

    response = requests.get(
        f"{base_url}=d",
        headers=_auth_headers(creds),
        timeout=120,
    )
    if not response.ok:
        _raise_api_error(response, "Download picked photo")
    destination.write_bytes(response.content)


def import_picked_photos(
    session_id: str,
    destination_dir: str | Path,
    token_path: str | Path | None = None,
) -> Path:
    """
    Download the first picked image from a completed Picker session.

    Requires the user to finish selecting photos in the Google Photos picker UI first.
    """
    creds = load_credentials(token_path)
    if creds is None:
        raise RuntimeError("Google Photos not connected — visit /google/connect first")

    session = get_picker_session(creds, session_id)
    if not session.get("mediaItemsSet"):
        raise RuntimeError("PICK_NOT_READY")

    items = list_picked_media_items(creds, session_id)
    photos = [
        item
        for item in items
        if (item.get("mediaFile") or item).get("mimeType", "").startswith("image/")
        or item.get("type") == "PHOTO"
    ]
    if not photos:
        raise RuntimeError("No photos were selected in the picker")

    item = random.choice(photos)
    media_file = item.get("mediaFile") or item
    filename = media_file.get("filename", "google_photo.jpg")
    stem = Path(filename).stem
    suffix = Path(filename).suffix.lower() or ".jpg"
    if suffix not in {".jpg", ".jpeg", ".png"}:
        suffix = ".jpg"

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    dest = Path(destination_dir) / f"google_{timestamp}_{stem}{suffix}"
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        _download_picked_item(creds, item, dest)
    finally:
        delete_picker_session(creds, session_id)

    logger.info("Imported picked Google Photo: %s", dest.name)
    return dest


def start_photo_pick(token_path: str | Path | None = None) -> tuple[str, str]:
    """
    Create a picker session.

    Returns (session_id, picker_uri_with_autoclose).
    """
    creds = load_credentials(token_path)
    if creds is None:
        raise RuntimeError("Google Photos not connected — visit /google/connect first")

    session = create_picker_session(creds)
    session_id = _session_id_from_response(session)
    picker_uri = session.get("pickerUri")
    if not session_id or not picker_uri:
        raise RuntimeError(f"Unexpected picker session response: {session}")

    if not picker_uri.rstrip("/").endswith("autoclose"):
        picker_uri = f"{picker_uri.rstrip('/')}/autoclose"

    return session_id, picker_uri


def disconnect(token_path: str | Path | None = None) -> None:
    """Remove stored Google OAuth credentials."""
    path = _token_path(token_path)
    if path.is_file():
        path.unlink()
        logger.info("Google Photos disconnected")

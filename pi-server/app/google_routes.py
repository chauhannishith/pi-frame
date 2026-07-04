"""Google Photos routes — OAuth connect and import."""

from __future__ import annotations

import secrets

from flask import Blueprint, redirect, request, session, url_for

from config import SOURCE_IMAGES_DIR
from frame_service import process_specific_image
from google_photos import (
    disconnect,
    exchange_code_for_credentials,
    fetch_random_photo,
    get_authorization_url,
    is_connected,
    is_google_photos_configured,
)

google_bp = Blueprint("google", __name__)

GOOGLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Google Photos — pi-frame</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 560px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
    nav {{ margin-bottom: 1.5rem; font-size: 0.9rem; }}
    nav a {{ margin-right: 1rem; }}
    .status {{ padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; font-size: 0.9rem; }}
    .connected {{ background: #e6f4ea; border: 1px solid #a8dab5; }}
    .disconnected {{ background: #fef7e0; border: 1px solid #fdd663; }}
    .unconfigured {{ background: #fce8e6; border: 1px solid #f5aca3; }}
    button, .btn {{
      background: #222; color: #fff; border: none; padding: 0.6rem 1.2rem;
      border-radius: 6px; cursor: pointer; font-size: 0.95rem; text-decoration: none; display: inline-block;
    }}
    button:hover, .btn:hover {{ background: #444; }}
    .btn-google {{ background: #1a73e8; }}
    form {{ margin-top: 1rem; }}
    code {{ background: #f4f4f4; padding: 0.1rem 0.3rem; border-radius: 3px; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <h1>Google Photos</h1>
  <nav>
    <a href="/gallery">Gallery</a>
    <a href="/google">Google Photos</a>
    <a href="/preview">Preview</a>
  </nav>

  {status_block}

  {actions}

  <p style="color:#666;font-size:0.85rem;margin-top:2rem">
    Requires Google Cloud OAuth credentials with the Photos Library API enabled.
    Set <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code> in your environment.
  </p>
</body>
</html>"""


def _render_google_page(status_html: str, actions_html: str) -> str:
    return GOOGLE_HTML.replace("{status_block}", status_html).replace("{actions}", actions_html)


@google_bp.route("/google", methods=["GET"])
def google_index():
    if not is_google_photos_configured():
        status = '<div class="status unconfigured">Google Photos is not configured. Add OAuth credentials to your environment.</div>'
        return _render_google_page(status, "")

    if is_connected():
        status = '<div class="status connected">Connected to Google Photos.</div>'
        actions = """
        <form method="post" action="/google/fetch">
          <button type="submit" class="btn-google">Import random photo &amp; CHANGE frame</button>
        </form>
        <form method="post" action="/google/fetch?library_only=1" style="margin-top:0.5rem">
          <button type="submit">Import random photo to library only</button>
        </form>
        <form method="post" action="/google/disconnect" style="margin-top:1.5rem">
          <button type="submit">Disconnect</button>
        </form>"""
    else:
        status = '<div class="status disconnected">Not connected to Google Photos.</div>'
        actions = '<a class="btn btn-google" href="/google/connect">Connect Google Photos</a>'

    msg = request.args.get("msg", "")
    err = request.args.get("err", "")
    if msg:
        status += f'<div class="status connected">{msg}</div>'
    if err:
        status += f'<div class="status unconfigured">{err}</div>'

    return _render_google_page(status, actions)


@google_bp.route("/google/connect", methods=["GET"])
def google_connect():
    if not is_google_photos_configured():
        return redirect(url_for("google.google_index", err="Google OAuth not configured."))

    state = secrets.token_urlsafe(32)
    session["google_oauth_state"] = state
    return redirect(get_authorization_url(state))


@google_bp.route("/google/callback", methods=["GET"])
def google_callback():
    if request.args.get("error"):
        return redirect(url_for("google.google_index", err="Google authorization was denied."))

    state = session.pop("google_oauth_state", None)
    if state is None or state != request.args.get("state"):
        return redirect(url_for("google.google_index", err="Invalid OAuth state."))

    code = request.args.get("code")
    if not code:
        return redirect(url_for("google.google_index", err="Missing authorization code."))

    try:
        exchange_code_for_credentials(code, state)
        return redirect(url_for("google.google_index", msg="Google Photos connected successfully."))
    except Exception:
        return redirect(url_for("google.google_index", err="Failed to complete Google authorization."))


@google_bp.route("/google/fetch", methods=["POST"])
def google_fetch():
    library_only = request.args.get("library_only") == "1"
    try:
        dest = fetch_random_photo(SOURCE_IMAGES_DIR)
        if library_only:
            return redirect(url_for("gallery.gallery_index", msg=f"Imported {dest.name} from Google Photos"))
        name = process_specific_image(dest)
        return redirect(url_for("gallery.gallery_view", filename=name, generated=1))
    except Exception as exc:
        return redirect(url_for("google.google_index", err=str(exc)))


@google_bp.route("/google/disconnect", methods=["POST"])
def google_disconnect():
    disconnect()
    return redirect(url_for("google.google_index", msg="Disconnected from Google Photos."))

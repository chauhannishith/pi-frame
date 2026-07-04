"""Google Photos routes — OAuth connect and picker import."""

from __future__ import annotations

from flask import Blueprint, redirect, request, url_for

from config import SOURCE_IMAGES_DIR
from frame_service import process_specific_image
from google_photos import (
    create_oauth_state,
    disconnect,
    exchange_code_for_credentials,
    get_authorization_url,
    import_picked_photos,
    is_connected,
    is_google_photos_configured,
    oauth_state_error,
    start_photo_pick,
)
from user_errors import format_user_error

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

  {footer}
</body>
</html>"""


def _missing_config_vars() -> list[str]:
    from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

    missing: list[str] = []
    if not GOOGLE_CLIENT_ID:
        missing.append("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_SECRET:
        missing.append("GOOGLE_CLIENT_SECRET")
    return missing


PICK_START_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="2;url={wait_url}">
  <title>Opening Google Photos picker — pi-frame</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 560px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
    .status {{ padding: 1rem; border-radius: 8px; background: #e8f0fe; border: 1px solid #aecbfa; font-size: 0.95rem; }}
    a.btn {{ background: #1a73e8; color: #fff; padding: 0.6rem 1.2rem; border-radius: 6px; text-decoration: none; display: inline-block; margin-top: 1rem; }}
  </style>
  <script>window.open("{picker_uri}", "_blank");</script>
</head>
<body>
  <h1>Pick a photo</h1>
  <div class="status">Opening Google Photos in a new tab…</div>
  <p style="color:#666;font-size:0.9rem;margin-top:1.5rem">
    Select one or more photos, then return to this tab — it will import automatically.
  </p>
  <a class="btn" href="{picker_uri}" target="_blank" rel="noopener">Open picker again</a>
  <p style="margin-top:1.5rem"><a href="/google">Cancel</a></p>
</body>
</html>"""


PICK_WAIT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="{refresh_seconds}">
  <title>Waiting for photo pick — pi-frame</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 560px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
    .status {{ padding: 1rem; border-radius: 8px; background: #fef7e0; border: 1px solid #fdd663; font-size: 0.95rem; }}
  </style>
</head>
<body>
  <h1>Pick a photo</h1>
  <div class="status">{message}</div>
  <p style="color:#666;font-size:0.9rem;margin-top:1.5rem">
    Finish selecting in the Google Photos window, then return here.
    This page refreshes automatically.
  </p>
  <p><a href="/google">Back to Google Photos</a></p>
</body>
</html>"""


def _config_checklist_html() -> str:
    """Show redirect URI hint when configured but not connected."""
    from config import FLASK_SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_REDIRECT_URI

    secret_ok = bool(FLASK_SECRET_KEY) and FLASK_SECRET_KEY != "dev-change-me-in-production"
    secret_note = "set" if secret_ok else "missing or still default — set FLASK_SECRET_KEY in .env"
    client_suffix = GOOGLE_CLIENT_ID[-20:] if len(GOOGLE_CLIENT_ID) >= 20 else GOOGLE_CLIENT_ID

    return f"""
  <p style="color:#666;font-size:0.85rem;margin-top:2rem">
    Open this app at <code>{GOOGLE_REDIRECT_URI.replace('/google/callback', '/google')}</code>
    (redirect URI must match Google Cloud exactly). FLASK_SECRET_KEY: {secret_note}.
    Client ID ends with <code>...{client_suffix}</code>.
  </p>"""


def _render_google_page(status_html: str, actions_html: str, footer_html: str = "") -> str:
    return (
        GOOGLE_HTML.replace("{status_block}", status_html)
        .replace("{actions}", actions_html)
        .replace("{footer}", footer_html)
    )


def _setup_footer_html() -> str:
    missing = _missing_config_vars()
    if not missing:
        return ""

    var_list = ", ".join(f"<code>{name}</code>" for name in missing)
    return f"""
  <p style="color:#666;font-size:0.85rem;margin-top:2rem">
    Missing: {var_list}. Enable the Photos Picker API in Google Cloud,
    create an OAuth Web client, and set these in <code>pi-server/.env</code>.
  </p>"""


def _footer_html() -> str:
    if not is_google_photos_configured():
        return _setup_footer_html()
    if is_connected():
        return ""
    return _config_checklist_html()


@google_bp.route("/google", methods=["GET"])
def google_index():
    if not is_google_photos_configured():
        missing = ", ".join(_missing_config_vars())
        status = (
            f'<div class="status unconfigured">Google Photos is not configured'
            f"{f' — missing {missing}' if missing else ''}.</div>"
        )
        return _render_google_page(status, "", _setup_footer_html())

    if is_connected():
        status = '<div class="status connected">Connected to Google Photos.</div>'
        actions = """
        <form method="post" action="/google/pick">
          <button type="submit" class="btn-google">Pick photo &amp; CHANGE frame</button>
        </form>
        <form method="post" action="/google/pick?library_only=1" style="margin-top:0.5rem">
          <button type="submit">Pick photo to library only</button>
        </form>
        <p style="color:#666;font-size:0.85rem;margin-top:0.75rem">
          Opens Google&apos;s photo picker — choose one or more photos, then return here to import.
        </p>
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

    return _render_google_page(status, actions, _footer_html())


@google_bp.route("/google/connect", methods=["GET"])
def google_connect():
    if not is_google_photos_configured():
        return redirect(url_for("google.google_index", err="Google OAuth not configured."))

    state = create_oauth_state()
    try:
        auth_url = get_authorization_url(state)
    except Exception as exc:
        return redirect(url_for("google.google_index", err=f"Could not start Google authorization: {format_user_error(exc)}"))
    return redirect(auth_url)


@google_bp.route("/google/callback", methods=["GET"])
def google_callback():
    if request.args.get("error"):
        desc = request.args.get("error_description") or request.args.get("error")
        return redirect(url_for("google.google_index", err=f"Google authorization denied: {desc}"))

    state = request.args.get("state")
    state_err = oauth_state_error(state)
    if state_err:
        return redirect(url_for("google.google_index", err=f"Invalid OAuth state: {state_err}"))

    code = request.args.get("code")
    if not code:
        return redirect(url_for("google.google_index", err="Missing authorization code."))

    try:
        exchange_code_for_credentials(code, state, authorization_response=request.url)
        return redirect(url_for("google.google_index", msg="Google Photos connected successfully."))
    except Exception as exc:
        return redirect(
            url_for("google.google_index", err=f"Failed to complete Google authorization: {format_user_error(exc)}")
        )


@google_bp.route("/google/pick", methods=["POST"])
def google_pick():
    library_only = request.args.get("library_only") == "1"
    try:
        session_id, picker_uri = start_photo_pick()
    except Exception as exc:
        return redirect(url_for("google.google_index", err=format_user_error(exc)))

    wait_url = url_for(
        "google.google_pick_wait",
        session_id=session_id,
        library_only=1 if library_only else 0,
    )
    return PICK_START_HTML.format(picker_uri=picker_uri, wait_url=wait_url)


@google_bp.route("/google/pick/wait/<session_id>", methods=["GET"])
def google_pick_wait(session_id: str):
    library_only = request.args.get("library_only") == "1"
    try:
        dest = import_picked_photos(session_id, SOURCE_IMAGES_DIR)
        if library_only:
            return redirect(url_for("gallery.gallery_index", msg=f"Imported {dest.name} from Google Photos"))
        name = process_specific_image(dest)
        return redirect(url_for("gallery.gallery_view", filename=name, generated=1))
    except RuntimeError as exc:
        if str(exc) == "PICK_NOT_READY":
            return PICK_WAIT_HTML.format(
                refresh_seconds=3,
                message="Waiting for your photo selection…",
            )
        return redirect(url_for("google.google_index", err=format_user_error(exc)))
    except Exception as exc:
        return redirect(url_for("google.google_index", err=format_user_error(exc)))


@google_bp.route("/google/disconnect", methods=["POST"])
def google_disconnect():
    disconnect()
    return redirect(url_for("google.google_index", msg="Disconnected from Google Photos."))

"""Google Photos routes — OAuth connect and picker import."""

from __future__ import annotations

import html

from flask import Blueprint, redirect, request, url_for

from config import SOURCE_IMAGES_DIR
from frame_service import process_specific_image
from google_photos import (
    create_oauth_state,
    disconnect,
    exchange_code_for_credentials,
    get_authorization_url,
    get_picker_session,
    import_picked_photos,
    is_connected,
    is_google_photos_configured,
    load_credentials,
    oauth_state_error,
    picker_uri_with_autoclose,
    start_photo_pick,
)
from settings_store import get_default_dither_method
from user_errors import format_user_error
from ui.layout import page_shell

google_bp = Blueprint("google", __name__)


def _missing_config_vars() -> list[str]:
    from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

    missing: list[str] = []
    if not GOOGLE_CLIENT_ID:
        missing.append("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_SECRET:
        missing.append("GOOGLE_CLIENT_SECRET")
    return missing


def _config_checklist_html() -> str:
    from config import FLASK_SECRET_KEY, GOOGLE_CLIENT_ID, GOOGLE_REDIRECT_URI

    secret_ok = bool(FLASK_SECRET_KEY) and FLASK_SECRET_KEY != "dev-change-me-in-production"
    secret_note = "set" if secret_ok else "missing or still default — set FLASK_SECRET_KEY in .env"
    client_suffix = GOOGLE_CLIENT_ID[-20:] if len(GOOGLE_CLIENT_ID) >= 20 else GOOGLE_CLIENT_ID

    return f"""
<p style="color:var(--on-surface-muted);font-size:0.85rem;margin-top:1.5rem;line-height:1.6">
  Open this app at <code>{html.escape(GOOGLE_REDIRECT_URI.replace('/google/callback', '/google'))}</code>
  (redirect URI must match Google Cloud exactly). FLASK_SECRET_KEY: {secret_note}.
  Client ID ends with <code>...{html.escape(client_suffix)}</code>.
</p>"""


def _setup_footer_html() -> str:
    missing = _missing_config_vars()
    if not missing:
        return ""

    var_list = ", ".join(f"<code>{html.escape(name)}</code>" for name in missing)
    return f"""
<p style="color:var(--on-surface-muted);font-size:0.85rem;margin-top:1.5rem;line-height:1.6">
  Missing: {var_list}. Enable the Photos Picker API in Google Cloud,
  create an OAuth Web client, and set these in <code>pi-server/.env</code>.
</p>"""


def _render_google_page(
    status_html: str,
    actions_html: str,
    footer_html: str = "",
    flash: str = "",
    flash_kind: str = "ok",
) -> str:
    body = f"""
<h1 style="font-size:1.5rem;margin-bottom:0.35rem">Google Photos</h1>
<p style="color:var(--on-surface-muted);margin-bottom:1.25rem;line-height:1.5">
  Import photos from your Google library using the official picker. Selections are copied into the local rotation library.
</p>
{status_html}
{actions_html}
{footer_html}"""

    return page_shell(
        title="Google Photos",
        nav_active="google",
        body_html=body,
        flash=flash,
        flash_kind=flash_kind,
        use_sidebar=False,
        show_change=True,
    )


def _render_pick_wait(session_id: str, library_only: bool, message: str) -> str:
    creds = load_credentials()
    if creds is None:
        raise RuntimeError("Google Photos not connected — visit /google/connect first")

    session = get_picker_session(creds, session_id)
    picker_uri = html.escape(picker_uri_with_autoclose(session.get("pickerUri", "")))
    refresh_seconds = _poll_interval_seconds(session)
    wait_url = html.escape(url_for(
        "google.google_pick_wait",
        session_id=session_id,
        library_only=1 if library_only else 0,
    ))

    body = f"""
<h1 style="font-size:1.5rem;margin-bottom:0.75rem">Pick photos</h1>
<div class="status-pill status-disconnected">{html.escape(message)}</div>
<ol style="color:var(--on-surface-muted);font-size:0.92rem;line-height:1.7;padding-left:1.2rem;margin-bottom:1.25rem">
  <li>Click <strong>Open Google Photos</strong> below</li>
  <li>Select one or more photos, then confirm</li>
  <li>Return to this tab — import runs automatically</li>
</ol>
<p><a class="btn btn-primary" href="{picker_uri}" target="_blank" rel="noopener">Open Google Photos</a></p>
<p style="color:var(--on-surface-muted);font-size:0.85rem;margin-top:1.5rem">
  Checking every {refresh_seconds}s for your selection…
</p>
<p style="margin-top:1rem"><a href="/google">Cancel</a></p>"""

    return page_shell(
        title="Pick photos",
        nav_active="google",
        body_html=body,
        use_sidebar=False,
        show_change=False,
        extra_head=f'<meta http-equiv="refresh" content="{refresh_seconds};url={wait_url}">',
    )


def _poll_interval_seconds(session: dict) -> int:
    raw = session.get("pollingConfig", {}).get("pollInterval", "5s")
    try:
        return max(3, int(str(raw).rstrip("s")))
    except ValueError:
        return 5


@google_bp.route("/google", methods=["GET"])
def google_index():
    msg = request.args.get("msg", "")
    err = request.args.get("err", "")

    if not is_google_photos_configured():
        missing = ", ".join(_missing_config_vars())
        status = (
            f'<div class="status-pill status-unconfigured">Google Photos is not configured'
            f"{f' — missing {html.escape(missing)}' if missing else ''}.</div>"
        )
        return _render_google_page(status, "", _setup_footer_html(), flash=err or msg, flash_kind="err" if err else "ok")

    if is_connected():
        status = '<div class="status-pill status-connected">Connected to Google Photos.</div>'
        actions = """
<div class="panel form-stack">
  <form method="post" action="/google/pick">
    <button type="submit" class="btn btn-primary">Pick photos &amp; push first to frame</button>
  </form>
  <form method="post" action="/google/pick?library_only=1" style="margin-top:0.75rem">
    <button type="submit" class="btn btn-secondary">Pick photos to library only</button>
  </form>
  <p style="color:var(--on-surface-muted);font-size:0.85rem;margin-top:0.75rem;line-height:1.5">
    Select photos in Google&apos;s picker — pi-frame imports your full selection into the library for rotation.
  </p>
  <form method="post" action="/google/disconnect" style="margin-top:1.25rem">
    <button type="submit" class="btn btn-ghost">Disconnect</button>
  </form>
</div>"""
    else:
        status = '<div class="status-pill status-disconnected">Not connected to Google Photos.</div>'
        actions = '<a class="btn btn-primary" href="/google/connect">Connect Google Photos</a>'

    footer = _config_checklist_html() if not is_connected() else ""
    return _render_google_page(status, actions, footer, flash=err or msg, flash_kind="err" if err else "ok")


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
        session_id, _picker_uri = start_photo_pick()
    except Exception as exc:
        return redirect(url_for("google.google_index", err=format_user_error(exc)))

    return redirect(
        url_for(
            "google.google_pick_wait",
            session_id=session_id,
            library_only=1 if library_only else 0,
        )
    )


@google_bp.route("/google/pick/wait/<session_id>", methods=["GET"])
def google_pick_wait(session_id: str):
    library_only = request.args.get("library_only") == "1"
    try:
        imported = import_picked_photos(session_id, SOURCE_IMAGES_DIR)
        if library_only:
            count = len(imported)
            label = "photo" if count == 1 else "photos"
            return redirect(
                url_for(
                    "gallery.gallery_index",
                    msg=f"Imported {count} {label} from Google Photos",
                )
            )
        name = process_specific_image(imported[0], dither_method=get_default_dither_method())
        return redirect(url_for("gallery.gallery_view", filename=name, generated=1))
    except RuntimeError as exc:
        if str(exc) == "PICK_NOT_READY":
            return _render_pick_wait(
                session_id,
                library_only,
                "Waiting for your photo selection…",
            )
        return redirect(url_for("google.google_index", err=format_user_error(exc)))
    except Exception as exc:
        return redirect(url_for("google.google_index", err=format_user_error(exc)))


@google_bp.route("/google/disconnect", methods=["POST"])
def google_disconnect():
    disconnect()
    return redirect(url_for("google.google_index", msg="Disconnected from Google Photos."))

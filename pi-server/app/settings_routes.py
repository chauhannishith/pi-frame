"""Settings page — default dither method."""

from __future__ import annotations

from flask import Blueprint, redirect, request, url_for

from frame_service import format_quick_action_message, toggle_frame_dither, toggle_frame_orientation
from processing.frame_orientation import orientation_label
from settings_store import (
    get_active_dither_method,
    get_default_dither_method,
    get_frame_orientation,
    set_default_dither_method,
)
from ui.dither_controls import dither_method_label, dither_toggle_html
from ui.layout import page_shell
from ui.orientation_controls import orientation_toggle_html

settings_bp = Blueprint("settings", __name__)


def _render_settings(flash: str = "", flash_kind: str = "ok") -> str:
    dither = get_default_dither_method()
    frame_orientation = get_frame_orientation()
    active_dither = get_active_dither_method()
    fs_checked = " checked" if dither == "floyd_steinberg" else ""
    at_checked = " checked" if dither == "atkinson" else ""
    dither_html = dither_toggle_html(
        active_dither,
        action="/settings/dither",
        full_width=True,
    )
    orientation_html = orientation_toggle_html(
        frame_orientation,
        action="/settings/orientation",
        full_width=True,
    )

    body = f"""
<h1 style="font-size:1.5rem;margin-bottom:0.35rem">Settings</h1>
<p style="color:var(--on-surface-muted);margin-bottom:1.5rem;line-height:1.5">
  Default processing options for CHANGE and push-to-frame.
  The driver wake schedule is set in ESP32 firmware (24h timer or GPIO 12 button).
</p>

<div class="panel form-stack settings-quick-actions-mobile">
  <h3>Quick actions</h3>
  <p class="sub">Switch orientation or dither and update <code>latest_frame.bin</code> for the active image.</p>
  <div class="quick-actions">
    {dither_html}
    {orientation_html}
  </div>
</div>

<form method="post" action="/settings" class="panel form-stack">
  <h3>Default dither method</h3>
  <p class="sub">Used for CHANGE and push-to-frame unless overridden per image.</p>
  <div class="dither-toggle">
    <label>
      <input type="radio" name="default_dither_method" value="floyd_steinberg"{fs_checked}>
      <span>Floyd-Steinberg</span>
    </label>
    <label>
      <input type="radio" name="default_dither_method" value="atkinson"{at_checked}>
      <span>Atkinson</span>
    </label>
  </div>

  <button type="submit" class="btn btn-primary">Save settings</button>
</form>

<div class="hint-card" style="margin-top:1.5rem">
  <strong>Physical display update</strong>
  Push to frame updates <code>latest_frame.bin</code> on the Pi.
  The ESP32 fetches it on wake — press the driver button for an immediate refresh.
</div>"""

    return page_shell(
        title="Settings",
        nav_active="settings",
        body_html=body,
        flash=flash,
        flash_kind=flash_kind,
        use_sidebar=False,
        show_change=True,
    )


@settings_bp.route("/settings", methods=["GET"])
def settings_index():
    msg = request.args.get("msg", "")
    err = request.args.get("err", "")
    if err:
        return _render_settings(err, "err")
    return _render_settings(msg)


@settings_bp.route("/settings", methods=["POST"])
def settings_save():
    dither = request.form.get("default_dither_method", "floyd_steinberg")

    try:
        set_default_dither_method(dither)
    except (ValueError, TypeError) as exc:
        return redirect(url_for("settings.settings_index", err=str(exc)))

    return redirect(url_for("settings.settings_index", msg="Settings saved."))


def _orientation_flash_message(new_orientation: str, preview_source: str | None) -> str:
    label = orientation_label(new_orientation)
    if preview_source:
        return format_quick_action_message(label, preview_source)
    return f"Frame orientation set to {label}."


@settings_bp.route("/settings/orientation", methods=["POST"])
def settings_orientation():
    try:
        new_orientation, preview_source = toggle_frame_orientation()
    except (ValueError, TypeError, OSError) as exc:
        return redirect(url_for("settings.settings_index", err=str(exc)))
    return redirect(url_for("settings.settings_index", msg=_orientation_flash_message(new_orientation, preview_source)))


def _dither_flash_message(new_method: str, preview_source: str | None) -> str:
    label = dither_method_label(new_method)
    if preview_source:
        return format_quick_action_message(label, preview_source)
    return f"Default dither method set to {label}."


@settings_bp.route("/settings/dither", methods=["POST"])
def settings_dither():
    try:
        new_method, preview_source = toggle_frame_dither()
    except (ValueError, TypeError, OSError) as exc:
        return redirect(url_for("settings.settings_index", err=str(exc)))
    return redirect(url_for("settings.settings_index", msg=_dither_flash_message(new_method, preview_source)))

"""Settings page — default dither method."""

from __future__ import annotations

from flask import Blueprint, redirect, request, url_for

from settings_store import get_default_dither_method, set_default_dither_method
from ui.layout import page_shell

settings_bp = Blueprint("settings", __name__)


def _render_settings(flash: str = "", flash_kind: str = "ok") -> str:
    dither = get_default_dither_method()
    fs_checked = " checked" if dither == "floyd_steinberg" else ""
    at_checked = " checked" if dither == "atkinson" else ""

    body = f"""
<h1 style="font-size:1.5rem;margin-bottom:0.35rem">Settings</h1>
<p style="color:var(--on-surface-muted);margin-bottom:1.5rem;line-height:1.5">
  Default processing options for CHANGE and push-to-frame.
  The driver wake schedule is set in ESP32 firmware (24h timer or GPIO 12 button).
</p>

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

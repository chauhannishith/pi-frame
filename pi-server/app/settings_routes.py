"""Settings page — Pi rotation interval and default dither method."""

from __future__ import annotations

import html

from flask import Blueprint, redirect, request, url_for

from settings_store import (
    get_default_dither_method,
    get_processing_interval_seconds,
    interval_preset_options,
    set_default_dither_method,
    set_processing_interval_seconds,
)
from ui.layout import page_shell

settings_bp = Blueprint("settings", __name__)


def _render_settings(flash: str = "", flash_kind: str = "ok") -> str:
    interval = get_processing_interval_seconds()
    dither = get_default_dither_method()
    presets = interval_preset_options()

    preset_options = []
    for key, seconds, label in presets:
        selected = " selected" if seconds == interval else ""
        preset_options.append(
            f'<option value="{seconds}"{selected}>{html.escape(label)}</option>'
        )

    custom_checked = " checked" if interval not in {s for _, s, _ in presets} else ""
    custom_value = interval if custom_checked else ""

    fs_checked = " checked" if dither == "floyd_steinberg" else ""
    at_checked = " checked" if dither == "atkinson" else ""

    body = f"""
<h1 style="font-size:1.5rem;margin-bottom:0.35rem">Settings</h1>
<p style="color:var(--on-surface-muted);margin-bottom:1.5rem;line-height:1.5">
  Control how often the Pi auto-rotates images and the default dithering for new processing.
  The ESP32 wake interval is configured in firmware only.
</p>

<form method="post" action="/settings" class="panel form-stack">
  <h3>Auto-rotate schedule</h3>
  <p class="sub">How often the background job advances to the next library image.</p>

  <label for="interval_preset">Preset</label>
  <select id="interval_preset" name="interval_preset">
    {"".join(preset_options)}
    <option value="custom"{custom_checked}>Custom</option>
  </select>

  <label for="interval_custom">Custom interval (seconds)</label>
  <input type="number" id="interval_custom" name="interval_custom" min="300" step="60"
    placeholder="e.g. 86400" value="{custom_value if custom_value else ''}">

  <h3 style="margin-top:1.25rem">Default dither method</h3>
  <p class="sub">Used for CHANGE, auto-rotate, and push-to-frame unless overridden per image.</p>
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
  Pushing or rotating updates <code>latest_frame.bin</code> on the Pi.
  Press the wake button on the ESP32 driver to fetch and refresh the e-ink panel.
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
    preset = request.form.get("interval_preset", "")
    custom = request.form.get("interval_custom", "").strip()
    dither = request.form.get("default_dither_method", "floyd_steinberg")

    try:
        if preset == "custom":
            if not custom:
                raise ValueError("Enter a custom interval in seconds")
            seconds = int(custom)
        else:
            seconds = int(preset)
        set_processing_interval_seconds(seconds)
        set_default_dither_method(dither)
    except (ValueError, TypeError) as exc:
        return redirect(url_for("settings.settings_index", err=str(exc)))

    return redirect(url_for("settings.settings_index", msg="Settings saved."))

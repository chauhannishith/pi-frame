"""Shared image view / dithered preview page."""

from __future__ import annotations

import html
import time

from config import FRAME_HEIGHT, FRAME_WIDTH
from ui.layout import page_shell

DITHER_OPTIONS = ("floyd_steinberg", "atkinson")

DITHER_LABELS = {
    "floyd_steinberg": "Floyd-Steinberg",
    "atkinson": "Atkinson",
    "default": "Default",
    "nearest": "Nearest",
}


def dither_method_label(method: str) -> str:
    return DITHER_LABELS.get(method, method)


def _dither_toggle_html(selected: str, form_id: str = "preview-form") -> str:
    options = []
    for value in DITHER_OPTIONS:
        checked = " checked" if value == selected else ""
        label = dither_method_label(value)
        options.append(f"""
    <label>
      <input type="radio" name="dither_method" value="{value}" form="{form_id}"{checked}>
      <span>{label}</span>
    </label>""")
    return f'<div class="dither-toggle">{"".join(options)}</div>'


def render_image_view_page(
    *,
    source_name: str,
    form_action: str,
    dither_method: str = "floyd_steinberg",
    show_dithered: bool = False,
    original_url: str | None = None,
    back_href: str = "/gallery",
    nav_active: str = "gallery",
    page_heading: str | None = None,
    show_controls: bool = True,
    flash: str = "",
    flash_kind: str = "ok",
) -> str:
    if dither_method not in DITHER_OPTIONS:
        dither_method = "floyd_steinberg"

    safe_name = html.escape(source_name)
    heading = html.escape(page_heading or source_name)
    cache_bust = int(time.time())

    dithered_block = ""
    if show_dithered:
        dithered_block = f"""
    <div class="view-panel dithered">
      <h3 style="font-size:0.95rem;margin-bottom:0.35rem">Dithered output</h3>
      <p class="sub" style="margin-bottom:0.75rem">{FRAME_WIDTH}×{FRAME_HEIGHT} · 6-color · {html.escape(dither_method_label(dither_method))}</p>
      <img class="preview-img-full" src="/preview.png?v={cache_bust}" width="{FRAME_WIDTH}" height="{FRAME_HEIGHT}" alt="Dithered preview">
    </div>"""

    original_block = ""
    if original_url:
        original_block = f"""
    <div class="view-panel original">
      <h3 style="font-size:0.95rem;margin-bottom:0.35rem">Original</h3>
      <p class="sub" style="margin-bottom:0.75rem">Source file</p>
      <img src="{html.escape(original_url)}" alt="Original" style="width:100%;max-width:240px;border-radius:0.75rem">
    </div>"""

    controls_block = ""
    if show_controls:
        controls_block = f"""
<div class="panel form-stack">
  <h3>Preview &amp; push</h3>
  <p class="sub">Generate preview to see the dithered result here. Push to frame updates <code>latest_frame.bin</code> — then press the driver wake button.</p>
  {_dither_toggle_html(dither_method)}
  <form id="preview-form" method="post" action="{html.escape(form_action)}">
    <div style="display:flex;flex-wrap:wrap;gap:0.75rem;margin-top:0.25rem">
      <button type="submit" name="action" value="preview" class="btn btn-secondary">Generate preview</button>
      <button type="submit" name="action" value="push" class="btn btn-primary">Push to frame</button>
    </div>
  </form>
</div>"""

    sub_text = (
        "Pick a dither method, generate a preview, or push to frame"
        if show_controls
        else f"{FRAME_WIDTH}×{FRAME_HEIGHT} · 6-color dithered output"
    )

    body = f"""
<h1 style="font-size:1.35rem;margin-bottom:0.25rem;word-break:break-all">{heading}</h1>
<p style="color:var(--on-surface-muted);font-size:0.88rem;margin-bottom:1.25rem">{sub_text}</p>

<div class="view-panels">
  {original_block}
  {dithered_block}
</div>

{controls_block}

<p style="margin-top:1.25rem;font-size:0.88rem"><a href="{html.escape(back_href)}">← Back</a></p>"""

    return page_shell(
        title=safe_name,
        nav_active=nav_active,
        body_html=body,
        flash=flash,
        flash_kind=flash_kind,
        use_sidebar=False,
        show_change=True,
    )

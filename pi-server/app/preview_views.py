"""Shared image view / dithered preview page."""

from __future__ import annotations

import html
import time

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
        <label class="toggle-option">
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
) -> str:
    """Render the unified full-view page with original, optional dithered preview, and generate controls."""
    if dither_method not in DITHER_OPTIONS:
        dither_method = "floyd_steinberg"

    safe_name = html.escape(source_name)
    heading = html.escape(page_heading or source_name)
    cache_bust = int(time.time())

    dithered_block = ""
    if show_dithered:
        dithered_block = f"""
        <div class="panel-view">
          <h2>Dithered preview</h2>
          <p class="hint">800×480 · 6-color · {html.escape(dither_method_label(dither_method))}</p>
          <img class="preview-img" src="/preview.png?v={cache_bust}" alt="Dithered preview">
        </div>"""

    original_block = ""
    if original_url:
        original_block = f"""
      <div class="panel-view">
        <h2>Original</h2>
        <p class="hint">Source file from library</p>
        <img class="original-img" src="{html.escape(original_url)}" alt="Original">
      </div>"""

    nav_gallery = "active" if nav_active == "gallery" else ""
    nav_preview = "active" if nav_active == "preview" else ""

    controls_block = ""
    if show_controls:
        controls_block = f"""
    <div class="controls">
      <h2>Generate dithered preview</h2>
      {_dither_toggle_html(dither_method)}
      <form id="preview-form" method="post" action="{html.escape(form_action)}">
        <button type="submit">Generate preview</button>
      </form>
    </div>"""

    sub_text = (
        "Full view · pick a dither method and click Generate preview"
        if show_controls
        else "800×480 · 6-color dithered output"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_name} — pi-frame</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      background: #f0f2f5;
      color: #1a1a1a;
      min-height: 100vh;
      padding: 2rem 1.25rem 3rem;
    }}
    .wrap {{ max-width: 920px; margin: 0 auto; }}
    h1 {{ font-size: 1.35rem; font-weight: 700; margin-bottom: 0.25rem; word-break: break-all; }}
    .sub {{ color: #5f6368; font-size: 0.88rem; margin-bottom: 1.25rem; }}

    nav {{ display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.5rem; }}
    nav a {{
      color: #3c4043; text-decoration: none; font-size: 0.88rem; font-weight: 500;
      padding: 0.45rem 0.9rem; border-radius: 999px; background: #fff;
      border: 1px solid #dadce0;
    }}
    nav a:hover {{ background: #e8f0fe; border-color: #aecbfa; color: #1a5fb4; }}
    nav a.active {{ background: #1a5fb4; color: #fff; border-color: #1a5fb4; }}

    .views {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1.25rem;
      margin-bottom: 1.25rem;
    }}
    .panel-view {{
      background: #fff;
      border: 1px solid #e0e0e0;
      border-radius: 12px;
      padding: 1rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .panel-view h2 {{ font-size: 0.92rem; font-weight: 600; color: #3c4043; margin-bottom: 0.35rem; }}
    .hint {{ font-size: 0.78rem; color: #80868b; margin-bottom: 0.75rem; }}
    .preview-img, .original-img {{
      display: block;
      width: 100%;
      border-radius: 8px;
      border: 1px solid #e8eaed;
      background: #eceff1;
    }}

    .controls {{
      background: #fff;
      border: 1px solid #e0e0e0;
      border-radius: 12px;
      padding: 1.15rem 1.25rem;
      margin-bottom: 1.25rem;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }}
    .controls h2 {{ font-size: 0.92rem; font-weight: 600; margin-bottom: 0.85rem; color: #3c4043; }}

    .dither-toggle {{
      display: flex;
      gap: 0.5rem;
      margin-bottom: 1rem;
      flex-wrap: wrap;
    }}
    .toggle-option {{
      flex: 1;
      min-width: 130px;
      cursor: pointer;
    }}
    .toggle-option input {{ display: none; }}
    .toggle-option span {{
      display: block;
      text-align: center;
      padding: 0.55rem 0.75rem;
      border-radius: 8px;
      border: 2px solid #dadce0;
      font-size: 0.82rem;
      font-weight: 500;
      color: #3c4043;
      transition: all 0.15s;
    }}
    .toggle-option input:checked + span {{
      border-color: #1a5fb4;
      background: #e8f0fe;
      color: #1a5fb4;
    }}

    button {{
      background: #1a5fb4;
      color: #fff;
      border: none;
      padding: 0.65rem 1.4rem;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.92rem;
      font-weight: 600;
    }}
    button:hover {{ background: #1557a0; }}

    .back {{ font-size: 0.88rem; }}
    .back a {{ color: #1a5fb4; text-decoration: none; }}
    .back a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class="wrap">
    <nav>
      <a href="/gallery" class="{nav_gallery}">Gallery</a>
      <a href="/google">Google Photos</a>
      <a href="/preview" class="{nav_preview}">Preview</a>
      <a href="/upload">Quick test upload</a>
    </nav>

    <h1>{heading}</h1>
    <p class="sub">{sub_text}</p>

    <div class="views">
      {original_block}
      {dithered_block}
    </div>

    {controls_block}

    <p class="back"><a href="{html.escape(back_href)}">← Back to gallery</a></p>
  </div>
</body>
</html>"""

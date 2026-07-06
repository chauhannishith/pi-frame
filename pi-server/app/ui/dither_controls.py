"""Shared dither method toggle UI."""

from __future__ import annotations

import html

DITHER_LABELS = {
    "floyd_steinberg": "Floyd-Steinberg",
    "atkinson": "Atkinson",
}


def dither_method_label(method: str) -> str:
    return DITHER_LABELS.get(method, method)


def dither_toggle_html(
    current: str,
    *,
    action: str,
    full_width: bool = False,
) -> str:
    current = current if current in DITHER_LABELS else "floyd_steinberg"
    other = "atkinson" if current == "floyd_steinberg" else "floyd_steinberg"
    other_label = dither_method_label(other)
    current_label = dither_method_label(current)
    btn_style = "width:100%" if full_width else ""

    return f"""
<div class="dither-quick-toggle">
  <p class="sub" style="margin-bottom:0.5rem">Dither: <strong>{html.escape(current_label)}</strong></p>
  <form method="post" action="{html.escape(action)}" style="margin:0">
    <button type="submit" class="btn btn-secondary" style="{btn_style}">Switch to {html.escape(other_label)}</button>
  </form>
</div>"""

"""Shared frame orientation toggle UI."""

from __future__ import annotations

import html

from processing.frame_orientation import normalize_orientation, orientation_label


def orientation_toggle_html(
    current: str,
    *,
    action: str | None = None,
    form_id: str | None = None,
    full_width: bool = False,
) -> str:
    current = normalize_orientation(current)
    other = "portrait" if current == "landscape" else "landscape"
    other_label = orientation_label(other)
    current_label = orientation_label(current)
    btn_style = "width:100%" if full_width else ""

    if action:
        return f"""
<div class="orientation-toggle">
  <p class="sub" style="margin-bottom:0.5rem">Orientation: <strong>{html.escape(current_label)}</strong></p>
  <form method="post" action="{html.escape(action)}" style="margin:0">
    <button type="submit" class="btn btn-secondary" style="{btn_style}">Switch to {html.escape(other_label)}</button>
  </form>
</div>"""

    if form_id:
        return f"""
<div class="orientation-toggle" style="margin-bottom:1rem">
  <p class="sub" style="margin-bottom:0.5rem">Frame orientation: <strong>{html.escape(current_label)}</strong></p>
  <button type="submit" name="action" value="orientation" class="btn btn-secondary" form="{html.escape(form_id)}">
    Switch to {html.escape(other_label)}
  </button>
</div>"""

    raise ValueError("orientation_toggle_html requires action or form_id")

"""Shared page shell, navigation, and flash messages."""

from __future__ import annotations

import html
from pathlib import Path

_NAV_ITEMS = (
    ("gallery", "Gallery", "/gallery"),
    ("google", "Google Photos", "/google"),
    ("settings", "Settings", "/settings"),
)

_THEME_CSS = (Path(__file__).parent / "theme.css").read_text()


def flash_html(message: str = "", kind: str = "ok") -> str:
    if not message:
        return ""
    css = "flash-ok" if kind == "ok" else "flash-err"
    return f'<div class="flash {css}">{html.escape(message)}</div>'


def top_header(nav_active: str = "gallery", *, show_change: bool = True) -> str:
    nav_links = []
    for key, label, href in _NAV_ITEMS:
        active = " active" if key == nav_active else ""
        nav_links.append(f'<a href="{href}" class="{active.strip()}">{label}</a>')
    nav_html = "\n".join(nav_links)

    change_btn = ""
    if show_change:
        change_btn = """
    <form method="post" action="/gallery/change" style="margin:0">
      <button type="submit" class="btn btn-primary">CHANGE</button>
    </form>"""

    return f"""
<header class="app-header">
  <a class="brand" href="/gallery">pi-frame</a>
  <nav class="top-nav">{nav_html}</nav>
  {change_btn}
</header>"""


def mobile_nav(nav_active: str = "gallery") -> str:
    icons = {
        "gallery": ("Gallery", "/gallery"),
        "google": ("Photos", "/google"),
        "settings": ("Settings", "/settings"),
    }
    links = []
    for key, (label, href) in icons.items():
        active = " active" if key == nav_active else ""
        links.append(f'<a href="{href}" class="{active.strip()}">{label}</a>')
    return f'<nav class="mobile-nav">{"".join(links)}</nav>'


def page_shell(
    *,
    title: str,
    nav_active: str = "gallery",
    body_html: str,
    sidebar_html: str = "",
    flash: str = "",
    flash_kind: str = "ok",
    extra_css: str = "",
    extra_head: str = "",
    extra_js: str = "",
    show_change: bool = True,
    use_sidebar: bool = True,
) -> str:
    safe_title = html.escape(title)
    flash_block = flash_html(flash, flash_kind)
    header = top_header(nav_active, show_change=show_change)
    mobile = mobile_nav(nav_active)

    if use_sidebar and sidebar_html:
        shell = f"""
<div class="app-shell">
  <aside class="sidebar">{sidebar_html}</aside>
  <main class="main-content">
    <div class="main-inner">{flash_block}{body_html}</div>
  </main>
</div>"""
    else:
        shell = f"""
<main class="main-content">
  <div class="main-inner narrow-page">{flash_block}{body_html}</div>
</main>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title} — pi-frame</title>
  {extra_head}
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>{_THEME_CSS}{extra_css}</style>
</head>
<body>
  {header}
  {shell}
  {mobile}
  {extra_js}
</body>
</html>"""


def gallery_sidebar(
    *,
    count: int,
    last_source: str,
    next_name: str,
    next_rotate_label: str,
    interval_hours: float,
) -> str:
    return f"""
<div class="sidebar-section">
  <p class="sidebar-label">Library</p>
  <div class="stat-card"><strong>{count}</strong> image(s)</div>
  <div class="stat-card">On frame: <strong>{html.escape(last_source)}</strong></div>
  <div class="stat-card">Next up: <strong>{html.escape(next_name)}</strong></div>
</div>
<div class="sidebar-section">
  <p class="sidebar-label">Schedule</p>
  <div class="stat-card">Auto-rotate every <strong>{interval_hours:g}h</strong></div>
  <div class="stat-card">{html.escape(next_rotate_label)}</div>
  <a class="btn btn-secondary" href="/settings" style="width:100%;margin-top:0.5rem">Edit schedule</a>
</div>
<div class="sidebar-section">
  <p class="sidebar-label">Display</p>
  <div class="hint-card">
    <strong>Update the physical frame</strong>
    After pushing an image here, press the <strong>wake button</strong> on the driver board to refresh the e-ink panel.
  </div>
</div>"""

"""Gallery routes — drive-like image library with CHANGE button."""

from __future__ import annotations

import html

from flask import Blueprint, abort, redirect, request, send_file, url_for

from config import DITHER_METHOD, SOURCE_IMAGES_DIR
from frame_service import change_frame, process_specific_image
from library import (
    add_to_library,
    delete_from_library,
    get_library_status,
    resolve_library_file,
)
from preview_views import DITHER_OPTIONS, render_image_view_page
from thumbnails import get_or_create_thumbnail

gallery_bp = Blueprint("gallery", __name__)

GALLERY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>pi-frame gallery</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: system-ui, -apple-system, sans-serif;
      background: #f0f2f5;
      color: #1a1a1a;
      min-height: 100vh;
      padding: 2rem 1.25rem 3rem;
    }
    .wrap { max-width: 960px; margin: 0 auto; }
    header { margin-bottom: 1.75rem; }
    h1 { font-size: 1.6rem; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 0.35rem; }
    .sub { color: #5f6368; font-size: 0.92rem; line-height: 1.5; }

    nav {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin: 1.25rem 0 1.75rem;
    }
    nav a {
      color: #3c4043;
      text-decoration: none;
      font-size: 0.88rem;
      font-weight: 500;
      padding: 0.45rem 0.9rem;
      border-radius: 999px;
      background: #fff;
      border: 1px solid #dadce0;
      transition: background 0.15s, border-color 0.15s;
    }
    nav a:hover { background: #e8f0fe; border-color: #aecbfa; color: #1a5fb4; }
    nav a.active { background: #1a5fb4; color: #fff; border-color: #1a5fb4; }

    .status {
      background: #fff;
      padding: 1rem 1.15rem;
      border-radius: 12px;
      margin-bottom: 1.25rem;
      font-size: 0.88rem;
      line-height: 1.7;
      border: 1px solid #e0e0e0;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .status strong { color: #1a5fb4; }

    .actions {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }
    .panel {
      padding: 1.15rem 1.25rem;
      border: 1px solid #e0e0e0;
      border-radius: 12px;
      background: #fff;
      box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .panel h2 { font-size: 0.95rem; font-weight: 600; margin-bottom: 0.85rem; color: #3c4043; }
    input[type="file"] { width: 100%; margin-bottom: 0.75rem; font-size: 0.85rem; }
    button, .btn {
      background: #3c4043;
      color: #fff;
      border: none;
      padding: 0.55rem 1.1rem;
      border-radius: 8px;
      cursor: pointer;
      font-size: 0.88rem;
      font-weight: 500;
      transition: background 0.15s;
    }
    button:hover { background: #202124; }
    .btn-change { background: #1a5fb4; padding: 0.7rem 1.6rem; font-size: 0.95rem; }
    .btn-change:hover { background: #1557a0; }
    .btn-danger { background: transparent; color: #c5221f; border: 1px solid #f5aca3; padding: 0.25rem 0.55rem; font-size: 0.75rem; }
    .btn-danger:hover { background: #fce8e6; }

    .section-title {
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 1rem;
      color: #3c4043;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 1.1rem;
    }

    .card {
      border: 2px solid #e8eaed;
      border-radius: 12px;
      overflow: hidden;
      background: #fff;
      box-shadow: 0 2px 6px rgba(0,0,0,0.06);
      transition: box-shadow 0.15s, border-color 0.15s;
    }
    .card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.1); }

    .card.active {
      border-color: #1a5fb4;
      box-shadow: 0 4px 14px rgba(26,95,180,0.22);
    }

    .thumb-wrap {
      position: relative;
      height: 150px;
      background: #eceff1;
      overflow: hidden;
    }
    .thumb-wrap img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }

    /* dog-ear corner on active card */
    .card.active .thumb-wrap::before {
      content: "";
      position: absolute;
      top: 0;
      right: 0;
      z-index: 2;
      width: 0;
      height: 0;
      border-style: solid;
      border-width: 0 42px 42px 0;
      border-color: transparent #1a5fb4 transparent transparent;
    }
    .card.active .thumb-wrap::after {
      content: "●";
      position: absolute;
      top: 7px;
      right: 9px;
      z-index: 3;
      color: #fff;
      font-size: 0.55rem;
      line-height: 1;
    }

    .badge-on-frame {
      display: none;
      position: absolute;
      bottom: 8px;
      left: 8px;
      z-index: 2;
      background: rgba(26, 95, 180, 0.92);
      color: #fff;
      font-size: 0.68rem;
      font-weight: 600;
      letter-spacing: 0.03em;
      text-transform: uppercase;
      padding: 3px 8px;
      border-radius: 4px;
    }
    .card.active .badge-on-frame { display: block; }

    .card-body {
      padding: 0.65rem 0.75rem 0.75rem;
      font-size: 0.78rem;
      color: #5f6368;
    }
    .card-name {
      display: block;
      font-weight: 500;
      color: #202124;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      margin-bottom: 0.15rem;
    }
    .card-meta { font-size: 0.72rem; color: #80868b; margin-bottom: 0.45rem; }
    .card-body form { margin: 0; }

    .thumb-link {
      display: block;
      color: inherit;
      text-decoration: none;
      cursor: pointer;
    }
    .thumb-link:hover .thumb-wrap img { opacity: 0.92; }

    .empty {
      color: #80868b;
      font-style: italic;
      padding: 3rem 2rem;
      text-align: center;
      border: 2px dashed #dadce0;
      border-radius: 12px;
      background: #fff;
    }
    .flash {
      padding: 0.75rem 1rem;
      border-radius: 10px;
      margin-bottom: 1.25rem;
      font-size: 0.88rem;
    }
    .flash-ok { background: #e6f4ea; border: 1px solid #a8dab5; color: #137333; }
    .flash-err { background: #fce8e6; border: 1px solid #f5aca3; color: #c5221f; }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <h1>Image library</h1>
      <p class="sub">Upload photos here — the frame cycles through them daily or when you hit CHANGE.</p>
    </header>

    <nav>
      <a href="/gallery" class="active">Gallery</a>
      <a href="/google">Google Photos</a>
      <a href="/preview">Preview</a>
      <a href="/upload">Quick test upload</a>
    </nav>

    {flash}

    <div class="status">
      <strong>{count}</strong> image(s) in library &nbsp;·&nbsp;
      On frame: <strong>{last_source}</strong><br>
      Last processed: {last_processed} &nbsp;·&nbsp;
      Next up: <strong>{next_name}</strong>
    </div>

    <div class="actions">
      <div class="panel">
        <h2>Change frame now</h2>
        <form method="post" action="/gallery/change">
          <button type="submit" class="btn-change">CHANGE</button>
        </form>
      </div>
      <div class="panel">
        <h2>Add images</h2>
        <form method="post" action="/gallery/upload" enctype="multipart/form-data">
          <input type="file" name="images" accept=".jpg,.jpeg,.png" multiple required>
          <button type="submit">Upload to library</button>
        </form>
      </div>
    </div>

    <p class="section-title">Library</p>
    {grid}
  </div>
</body>
</html>"""


def _render_card(img: dict, active_name: str | None) -> str:
    name = img["name"]
    safe_name = html.escape(name)
    is_active = active_name is not None and name == active_name
    active_class = " active" if is_active else ""
    return f"""
    <div class="card{active_class}">
      <a class="thumb-link" href="/gallery/view/{safe_name}">
        <div class="thumb-wrap">
          <span class="badge-on-frame">On frame</span>
          <img src="/gallery/thumb/{safe_name}" alt="{safe_name}" loading="lazy">
        </div>
      </a>
      <div class="card-body">
        <span class="card-name" title="{safe_name}">{safe_name}</span>
        <span class="card-meta">{img['size_kb']} KB</span>
        <form method="post" action="/gallery/delete/{safe_name}">
          <button type="submit" class="btn-danger" onclick="return confirm('Delete {safe_name}?')">Delete</button>
        </form>
      </div>
    </div>"""


def _render_gallery(flash: str = "", flash_class: str = "flash-ok") -> str:
    status = get_library_status(SOURCE_IMAGES_DIR)
    images = status["images"]
    next_idx = status["next_index"]
    next_name = images[next_idx]["name"] if images else "—"
    last_source = status["last_source"] or "—"
    last_processed = status["last_processed_at"] or "—"
    active_name = status.get("last_source")

    if images:
        cards = [_render_card(img, active_name) for img in images]
        grid = f'<div class="grid">{"".join(cards)}</div>'
    else:
        grid = '<div class="empty">No images yet — upload some photos or import from Google Photos.</div>'

    flash_html = f'<div class="flash {flash_class}">{html.escape(flash)}</div>' if flash else ""
    html_out = GALLERY_HTML
    html_out = html_out.replace("{flash}", flash_html)
    html_out = html_out.replace("{count}", str(status["count"]))
    html_out = html_out.replace("{last_source}", html.escape(str(last_source)))
    html_out = html_out.replace("{last_processed}", html.escape(str(last_processed)))
    html_out = html_out.replace("{next_name}", html.escape(str(next_name)))
    html_out = html_out.replace("{grid}", grid)
    return html_out


@gallery_bp.route("/gallery", methods=["GET"])
def gallery_index():
    msg = request.args.get("msg", "")
    err = request.args.get("err", "")
    if err:
        return _render_gallery(err, "flash-err")
    return _render_gallery(msg)


@gallery_bp.route("/gallery/upload", methods=["POST"])
def gallery_upload():
    uploads = request.files.getlist("images")
    uploads = [f for f in uploads if f.filename]

    if not uploads:
        return redirect(url_for("gallery.gallery_index", err="No files selected."))

    saved: list[str] = []
    skipped: list[str] = []

    for uploaded in uploads:
        try:
            dest = add_to_library(SOURCE_IMAGES_DIR, uploaded, uploaded.filename)
            saved.append(dest.name)
        except ValueError:
            skipped.append(uploaded.filename)

    if not saved:
        return redirect(url_for("gallery.gallery_index", err="No valid JPG or PNG files were uploaded."))

    if len(saved) == 1:
        msg = f"Uploaded {saved[0]}"
    else:
        msg = f"Uploaded {len(saved)} images"

    if skipped:
        msg += f" ({len(skipped)} skipped — unsupported type)"

    return redirect(url_for("gallery.gallery_index", msg=msg))


@gallery_bp.route("/gallery/delete/<filename>", methods=["POST"])
def gallery_delete(filename: str):
    if not delete_from_library(SOURCE_IMAGES_DIR, filename):
        return redirect(url_for("gallery.gallery_index", err=f"Could not delete {filename}"))
    return redirect(url_for("gallery.gallery_index", msg=f"Deleted {filename}"))


@gallery_bp.route("/gallery/change", methods=["POST"])
def gallery_change():
    name = change_frame()
    if name is None:
        return redirect(url_for("gallery.gallery_index", err="Library is empty — upload an image first."))
    return redirect(url_for("gallery.gallery_index", msg=f"Frame changed to {name}"))


@gallery_bp.route("/gallery/view/<filename>", methods=["GET", "POST"])
def gallery_view(filename: str):
    """Full-size view with dither method toggle and generate preview."""
    path = resolve_library_file(SOURCE_IMAGES_DIR, filename)
    if path is None:
        abort(404)

    dither_method = request.values.get("dither_method", "floyd_steinberg")
    if dither_method not in DITHER_OPTIONS:
        dither_method = "floyd_steinberg"

    if request.method == "POST":
        process_specific_image(path, dither_method=dither_method)
        return redirect(url_for(
            "gallery.gallery_view",
            filename=filename,
            generated=1,
            method=dither_method,
        ))

    show_dithered = request.args.get("generated") == "1"
    if show_dithered:
        dither_method = request.args.get("method", dither_method)
        if dither_method == "default":
            dither_method = DITHER_METHOD
        if dither_method not in DITHER_OPTIONS:
            dither_method = "floyd_steinberg"

    return render_image_view_page(
        source_name=filename,
        original_url=url_for("gallery.gallery_file", filename=filename),
        form_action=url_for("gallery.gallery_view", filename=filename),
        dither_method=dither_method,
        show_dithered=show_dithered,
    )


@gallery_bp.route("/gallery/thumb/<filename>", methods=["GET"])
def gallery_thumb(filename: str):
    path = resolve_library_file(SOURCE_IMAGES_DIR, filename)
    if path is None:
        abort(404)
    thumb = get_or_create_thumbnail(path)
    return send_file(thumb, mimetype="image/jpeg", max_age=86400)


@gallery_bp.route("/gallery/file/<filename>", methods=["GET"])
def gallery_file(filename: str):
    path = resolve_library_file(SOURCE_IMAGES_DIR, filename)
    if path is None:
        abort(404)
    return send_file(path)

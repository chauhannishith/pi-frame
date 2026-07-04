"""Gallery routes — drive-like image library with CHANGE button."""

from __future__ import annotations

from flask import Blueprint, abort, redirect, request, send_file, url_for

from config import SOURCE_IMAGES_DIR
from frame_service import change_frame
from library import (
    add_to_library,
    delete_from_library,
    get_library_status,
    resolve_library_file,
)
from thumbnails import get_or_create_thumbnail

gallery_bp = Blueprint("gallery", __name__)

GALLERY_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>pi-frame gallery</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; color: #222; }}
    h1 {{ font-size: 1.4rem; margin-bottom: 0.2rem; }}
    .sub {{ color: #666; font-size: 0.9rem; margin-bottom: 1.5rem; }}
    nav {{ margin-bottom: 1.5rem; font-size: 0.9rem; }}
    nav a {{ margin-right: 1rem; }}
    .status {{ background: #f4f4f4; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem; font-size: 0.9rem; }}
    .actions {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; align-items: flex-start; }}
    .panel {{ flex: 1; min-width: 260px; padding: 1rem; border: 1px solid #ddd; border-radius: 8px; background: #fafafa; }}
    .panel h2 {{ font-size: 1rem; margin: 0 0 0.75rem; }}
    input[type="file"] {{ width: 100%; margin-bottom: 0.75rem; }}
    button, .btn {{
      background: #222; color: #fff; border: none; padding: 0.55rem 1rem;
      border-radius: 6px; cursor: pointer; font-size: 0.9rem; text-decoration: none; display: inline-block;
    }}
    button:hover, .btn:hover {{ background: #444; }}
    .btn-change {{ background: #1a5fb4; font-size: 1rem; padding: 0.75rem 1.5rem; }}
    .btn-change:hover {{ background: #3584e4; }}
    .btn-danger {{ background: #c01c28; padding: 0.3rem 0.6rem; font-size: 0.8rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 1rem; }}
    .card {{ border: 1px solid #ddd; border-radius: 8px; overflow: hidden; background: #fff; }}
    .card img {{ width: 100%; height: 100px; object-fit: cover; display: block; background: #eee; }}
    .card-body {{ padding: 0.5rem; font-size: 0.75rem; }}
    .card-body form {{ margin-top: 0.4rem; }}
    .empty {{ color: #888; font-style: italic; padding: 2rem; text-align: center; border: 1px dashed #ccc; border-radius: 8px; }}
    .flash {{ padding: 0.75rem 1rem; border-radius: 6px; margin-bottom: 1rem; font-size: 0.9rem; }}
    .flash-ok {{ background: #e6f4ea; border: 1px solid #a8dab5; color: #137333; }}
    .flash-err {{ background: #fce8e6; border: 1px solid #f5aca3; color: #c5221f; }}
  </style>
</head>
<body>
  <h1>Image library</h1>
  <p class="sub">Upload photos here — the frame cycles through them daily or when you hit CHANGE.</p>
  <nav>
    <a href="/gallery">Gallery</a>
    <a href="/google">Google Photos</a>
    <a href="/preview">Preview</a>
    <a href="/upload">Quick test upload</a>
  </nav>

  {flash}

  <div class="status">
    <strong>{count}</strong> image(s) in library<br>
    Now showing: <strong>{last_source}</strong><br>
    Last processed: {last_processed}<br>
    Next in rotation: <strong>{next_name}</strong>
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

  <h2>Library</h2>
  {grid}
</body>
</html>"""


def _render_gallery(flash: str = "", flash_class: str = "flash-ok") -> str:
    status = get_library_status(SOURCE_IMAGES_DIR)
    images = status["images"]
    next_idx = status["next_index"]
    next_name = images[next_idx]["name"] if images else "—"
    last_source = status["last_source"] or "—"
    last_processed = status["last_processed_at"] or "—"

    if images:
        cards = []
        for img in images:
            cards.append(f"""
            <div class="card">
              <img src="/gallery/thumb/{img['name']}" alt="{img['name']}" loading="lazy">
              <div class="card-body">
                {img['name']}<br>{img['size_kb']} KB
                <form method="post" action="/gallery/delete/{img['name']}">
                  <button type="submit" class="btn-danger" onclick="return confirm('Delete {img['name']}?')">Delete</button>
                </form>
              </div>
            </div>""")
        grid = f'<div class="grid">{"".join(cards)}</div>'
    else:
        grid = '<div class="empty">No images yet — upload some photos or import from Google Photos.</div>'

    flash_html = f'<div class="flash {flash_class}">{flash}</div>' if flash else ""
    html = GALLERY_HTML
    html = html.replace("{flash}", flash_html)
    html = html.replace("{count}", str(status["count"]))
    html = html.replace("{last_source}", last_source)
    html = html.replace("{last_processed}", last_processed)
    html = html.replace("{next_name}", next_name)
    html = html.replace("{grid}", grid)
    return html


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
    return redirect(f"/preview?method=default&source={name}")


@gallery_bp.route("/gallery/thumb/<filename>", methods=["GET"])
def gallery_thumb(filename: str):
    """Serve a small cached thumbnail (~120px JPEG)."""
    path = resolve_library_file(SOURCE_IMAGES_DIR, filename)
    if path is None:
        abort(404)
    thumb = get_or_create_thumbnail(path)
    return send_file(thumb, mimetype="image/jpeg", max_age=86400)


@gallery_bp.route("/gallery/file/<filename>", methods=["GET"])
def gallery_file(filename: str):
    """Serve the original full-size library image."""
    path = resolve_library_file(SOURCE_IMAGES_DIR, filename)
    if path is None:
        abort(404)
    return send_file(path)

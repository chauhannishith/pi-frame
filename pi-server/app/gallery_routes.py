"""Gallery routes — Stitch-inspired library hub."""

from __future__ import annotations

import html
import os
import time

from flask import Blueprint, abort, redirect, request, send_file, url_for

from config import PREVIEW_PATH, SOURCE_IMAGES_DIR
from frame_service import change_frame, process_specific_image
from settings_store import (
    format_next_rotation,
    get_default_dither_method,
    get_processing_interval_seconds,
)
from user_errors import format_user_error
from library import (
    add_to_library,
    delete_from_library,
    delete_many_from_library,
    get_library_status,
    resolve_library_file,
)
from preview_views import render_image_view_page
from thumbnails import get_or_create_thumbnail
from ui.layout import gallery_sidebar, page_shell

gallery_bp = Blueprint("gallery", __name__)

_GALLERY_JS = """
<script>
document.addEventListener("DOMContentLoaded", function () {
  var bulkForm = document.getElementById("bulk-delete-form");
  var selectAll = document.getElementById("select-all");
  var deleteBtn = document.getElementById("bulk-delete-btn");
  var countEl = document.getElementById("sel-count");
  if (!bulkForm || !selectAll || !deleteBtn) return;

  function boxes() {
    return Array.prototype.slice.call(document.querySelectorAll(".card-select-input"));
  }

  function selectedCount() {
    return boxes().filter(function (b) { return b.checked; }).length;
  }

  function syncUI() {
    var count = selectedCount();
    var total = boxes().length;
    countEl.textContent = String(count);
    deleteBtn.disabled = count === 0;
    selectAll.checked = total > 0 && count === total;
    selectAll.indeterminate = count > 0 && count < total;
    boxes().forEach(function (box) {
      var card = box.closest(".photo-card");
      if (card) card.classList.toggle("selected", box.checked);
    });
  }

  selectAll.addEventListener("change", function () {
    var checked = selectAll.checked;
    boxes().forEach(function (box) { box.checked = checked; });
    syncUI();
  });

  boxes().forEach(function (box) {
    box.addEventListener("change", syncUI);
  });

  bulkForm.addEventListener("submit", function (event) {
    var count = selectedCount();
    if (count === 0) {
      event.preventDefault();
      return;
    }
    if (!confirm("Delete " + count + " selected image(s)?")) {
      event.preventDefault();
    }
  });

  syncUI();
});
</script>"""


def _sort_images(images: list[dict], filter_mode: str) -> list[dict]:
    if filter_mode == "recent":
        return sorted(images, key=lambda i: i["mtime"], reverse=True)
    return sorted(images, key=lambda i: i["name"].lower())


def _render_card(img: dict, active_name: str | None) -> str:
    name = img["name"]
    safe_name = html.escape(name)
    is_on_frame = active_name is not None and name == active_name
    on_frame_class = " on-frame" if is_on_frame else ""
    badge = '<span class="badge badge-frame">On frame</span>' if is_on_frame else '<span class="badge badge-library">In library</span>'

    return f"""
<div class="photo-card{on_frame_class}">
  <label class="card-select" title="Select for deletion">
    <input type="checkbox" class="card-select-input" name="filenames" value="{safe_name}" form="bulk-delete-form">
  </label>
  <a href="/gallery/view/{safe_name}">
    <div class="thumb-box">
      {badge}
      <img src="/gallery/thumb/{safe_name}" alt="{safe_name}" loading="lazy">
    </div>
  </a>
  <div class="card-foot">
    <span class="card-name" title="{safe_name}">{safe_name}</span>
    <div class="card-actions">
      <form method="post" action="/gallery/push/{safe_name}" style="margin:0">
        <button type="submit" class="btn btn-ghost" title="Push to frame">Push</button>
      </form>
      <form method="post" action="/gallery/delete/{safe_name}" style="margin:0">
        <button type="submit" class="btn btn-danger" onclick="return confirm('Delete {safe_name}?')">Del</button>
      </form>
    </div>
  </div>
</div>"""


def _frame_preview_block(last_source: str | None) -> str:
    if not last_source or not os.path.isfile(PREVIEW_PATH):
        return ""
    cache_bust = int(time.time())
    safe = html.escape(last_source)
    return f"""
<div class="panel">
  <h3>Current frame</h3>
  <p class="sub">{safe} — press the driver wake button to refresh the display</p>
  <div class="frame-preview-section">
    <div class="frame-bezel">
      <div class="frame-bezel-inner">
        <img src="/preview.png?v={cache_bust}" alt="Current frame preview">
      </div>
      <p class="frame-bezel-label">pi-frame · 7.3&quot;</p>
    </div>
  </div>
</div>"""


def _render_gallery(
    flash: str = "",
    flash_kind: str = "ok",
    filter_mode: str = "all",
) -> str:
    status = get_library_status(SOURCE_IMAGES_DIR)
    images = _sort_images(status["images"], filter_mode)
    next_idx = status["next_index"]
    next_name = status["images"][next_idx]["name"] if status["images"] else "—"
    last_source = status["last_source"] or "—"
    active_name = status.get("last_source")
    interval = get_processing_interval_seconds()
    interval_hours = interval / 3600
    rotate_label = format_next_rotation(status.get("last_processed_at"), interval)

    all_active = "active" if filter_mode != "recent" else ""
    recent_active = "active" if filter_mode == "recent" else ""

    if images:
        bulk_bar = """
<form id="bulk-delete-form" method="post" action="/gallery/delete-selected">
  <div class="bulk-bar">
    <label style="display:flex;align-items:center;gap:0.45rem;font-size:0.85rem;cursor:pointer">
      <input type="checkbox" id="select-all"> Select all
    </label>
    <button type="submit" class="btn btn-danger" id="bulk-delete-btn" disabled>
      Delete selected (<span id="sel-count">0</span>)
    </button>
  </div>
</form>"""
        cards = [_render_card(img, active_name) for img in images]
        upload_tile = """
<label class="upload-tile" for="gallery-upload-input">
  <span style="font-size:1.5rem;line-height:1">+</span>
  <span style="font-size:0.82rem;font-weight:600;margin-top:0.35rem">Add photos</span>
</label>"""
        grid = f'<div class="photo-grid">{upload_tile}{"".join(cards)}</div>'
    else:
        bulk_bar = ""
        grid = """
<div class="empty-state">
  <p style="margin-bottom:1rem">No images yet — upload photos or import from Google Photos.</p>
  <form method="post" action="/gallery/upload" enctype="multipart/form-data" class="form-stack" style="max-width:20rem;margin:0 auto;text-align:left">
    <input type="file" name="images" accept=".jpg,.jpeg,.png" multiple required>
    <button type="submit" class="btn btn-primary">Upload to library</button>
  </form>
</div>"""

    hero_upload = ""
    if images:
        hero_upload = """
<form id="gallery-upload-form" method="post" action="/gallery/upload" enctype="multipart/form-data" style="display:none">
  <input id="gallery-upload-input" type="file" name="images" accept=".jpg,.jpeg,.png" multiple
    onchange="if(this.files.length) this.form.submit()">
</form>"""

    body = f"""
{hero_upload}
<div class="hero">
  <h2>Gallery</h2>
  <p>Upload and manage photos for your e-ink frame. Use <strong>CHANGE</strong> to rotate, or <strong>Push</strong> on any card to set that image as the next frame output.</p>
  <div class="hero-actions">
    <a class="btn btn-secondary" href="/google">Import from Google</a>
  </div>
</div>

{_frame_preview_block(status.get("last_source"))}

<div class="section-head">
  <div>
    <h3 style="font-size:1.1rem">Library</h3>
    <p class="sub" style="margin:0">{status["count"]} image(s)</p>
  </div>
  <div class="filter-chips">
    <a href="/gallery?filter=all" class="{all_active.strip()}">All</a>
    <a href="/gallery?filter=recent" class="{recent_active.strip()}">Recent</a>
  </div>
</div>

{bulk_bar}
{grid}"""

    sidebar = gallery_sidebar(
        count=status["count"],
        last_source=str(last_source),
        next_name=str(next_name),
        next_rotate_label=rotate_label,
        interval_hours=interval_hours,
    )

    return page_shell(
        title="Gallery",
        nav_active="gallery",
        body_html=body,
        sidebar_html=sidebar,
        flash=flash,
        flash_kind=flash_kind,
        extra_js=_GALLERY_JS,
        show_change=True,
    )


@gallery_bp.route("/gallery", methods=["GET"])
def gallery_index():
    msg = request.args.get("msg", "")
    err = request.args.get("err", "")
    filter_mode = request.args.get("filter", "all")
    if filter_mode not in ("all", "recent"):
        filter_mode = "all"
    if err:
        return _render_gallery(err, "err", filter_mode)
    return _render_gallery(msg, "ok", filter_mode)


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


@gallery_bp.route("/gallery/delete-selected", methods=["POST"])
def gallery_delete_selected():
    names = request.form.getlist("filenames")
    if not names:
        return redirect(url_for("gallery.gallery_index", err="No images selected."))

    deleted, failed = delete_many_from_library(SOURCE_IMAGES_DIR, names)
    if deleted == 0:
        return redirect(url_for("gallery.gallery_index", err="Could not delete selected images."))

    label = "image" if deleted == 1 else "images"
    msg = f"Deleted {deleted} {label}"
    if failed:
        msg += f" ({len(failed)} not found)"
    return redirect(url_for("gallery.gallery_index", msg=msg))


@gallery_bp.route("/gallery/delete/<filename>", methods=["POST"])
def gallery_delete(filename: str):
    if not delete_from_library(SOURCE_IMAGES_DIR, filename):
        return redirect(url_for("gallery.gallery_index", err=f"Could not delete {filename}"))
    return redirect(url_for("gallery.gallery_index", msg=f"Deleted {filename}"))


@gallery_bp.route("/gallery/change", methods=["POST"])
def gallery_change():
    try:
        name = change_frame(dither_method=get_default_dither_method())
    except Exception as exc:
        return redirect(url_for("gallery.gallery_index", err=f"Frame change failed: {format_user_error(exc)}"))
    if name is None:
        return redirect(url_for("gallery.gallery_index", err="Library is empty — upload an image first."))
    return redirect(url_for("gallery.gallery_index", msg=f"Frame changed to {name}. Press the driver wake button to update the display."))


@gallery_bp.route("/gallery/push/<filename>", methods=["POST"])
def gallery_push(filename: str):
    path = resolve_library_file(SOURCE_IMAGES_DIR, filename)
    if path is None:
        return redirect(url_for("gallery.gallery_index", err=f"Image not found: {filename}"))
    try:
        process_specific_image(path, dither_method=get_default_dither_method())
    except Exception as exc:
        return redirect(url_for("gallery.gallery_index", err=f"Push failed: {format_user_error(exc)}"))
    return redirect(url_for("gallery.gallery_index", msg=f"Pushed {filename} to frame. Press the driver wake button to update the display."))


@gallery_bp.route("/gallery/view/<filename>", methods=["GET", "POST"])
def gallery_view(filename: str):
    path = resolve_library_file(SOURCE_IMAGES_DIR, filename)
    if path is None:
        abort(404)

    dither_method = request.values.get("dither_method", get_default_dither_method())
    if dither_method not in ("floyd_steinberg", "atkinson"):
        dither_method = get_default_dither_method()

    if request.method == "POST":
        try:
            process_specific_image(path, dither_method=dither_method)
        except Exception as exc:
            return redirect(url_for("gallery.gallery_index", err=f"Push failed: {format_user_error(exc)}"))
        return redirect(url_for(
            "gallery.gallery_view",
            filename=filename,
            generated=1,
            method=dither_method,
        ))

    show_dithered = request.args.get("generated") == "1"
    if show_dithered:
        dither_method = request.args.get("method", dither_method)
        if dither_method not in ("floyd_steinberg", "atkinson"):
            dither_method = get_default_dither_method()

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

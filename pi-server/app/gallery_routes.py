"""Gallery routes — Stitch-inspired library hub."""

from __future__ import annotations

import html

from flask import Blueprint, abort, redirect, request, send_file, url_for

from config import SOURCE_IMAGES_DIR
from frame_service import (
    change_frame,
    format_quick_action_message,
    generate_preview,
    process_specific_image,
    toggle_frame_dither,
    toggle_frame_orientation,
)
from processing.frame_orientation import orientation_label
from settings_store import (
    format_frame_output_status,
    get_active_dither_method,
    get_default_dither_method,
    get_frame_orientation,
    set_frame_orientation,
)
from ui.dither_controls import dither_method_label
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
      <a href="/gallery/view/{safe_name}" class="btn btn-ghost" title="Preview dithering">Preview</a>
      <form method="post" action="/gallery/delete/{safe_name}" style="margin:0">
        <button type="submit" class="btn btn-danger" onclick="return confirm('Delete {safe_name}?')">Del</button>
      </form>
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
    frame_status, frame_filename, frame_time = format_frame_output_status(
        status.get("last_source"),
        status.get("last_processed_at"),
    )

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
  <p>Upload photos, click <strong>Preview</strong> on any image to test dithering, then <strong>Push to frame</strong> when you are ready. Nothing updates the display until you push.</p>
  <div class="hero-actions">
    <a class="btn btn-secondary" href="/google">Import from Google</a>
  </div>
</div>

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
        frame_status=frame_status,
        frame_filename=frame_filename,
        frame_time=frame_time,
        frame_orientation=get_frame_orientation(),
        dither_method=get_active_dither_method(),
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


def _orientation_flash_message(new_orientation: str, preview_source: str | None) -> str:
    label = orientation_label(new_orientation)
    if preview_source:
        return format_quick_action_message(label, preview_source)
    return f"Frame orientation set to {label}."


@gallery_bp.route("/gallery/orientation", methods=["POST"])
def gallery_orientation():
    try:
        new_orientation, preview_source = toggle_frame_orientation()
    except Exception as exc:
        return redirect(url_for("gallery.gallery_index", err=f"Orientation change failed: {format_user_error(exc)}"))
    return redirect(url_for("gallery.gallery_index", msg=_orientation_flash_message(new_orientation, preview_source)))


def _dither_flash_message(new_method: str, preview_source: str | None) -> str:
    label = dither_method_label(new_method)
    if preview_source:
        return format_quick_action_message(label, preview_source)
    return f"Default dither method set to {label}."


@gallery_bp.route("/gallery/dither", methods=["POST"])
def gallery_dither():
    try:
        new_method, preview_source = toggle_frame_dither()
    except Exception as exc:
        return redirect(url_for("gallery.gallery_index", err=f"Dither change failed: {format_user_error(exc)}"))
    return redirect(url_for("gallery.gallery_index", msg=_dither_flash_message(new_method, preview_source)))


@gallery_bp.route("/gallery/view/<filename>", methods=["GET", "POST"])
def gallery_view(filename: str):
    path = resolve_library_file(SOURCE_IMAGES_DIR, filename)
    if path is None:
        abort(404)

    dither_method = request.values.get("dither_method", get_default_dither_method())
    if dither_method not in ("floyd_steinberg", "atkinson"):
        dither_method = get_default_dither_method()
    frame_orientation = get_frame_orientation()

    if request.method == "POST":
        action = request.form.get("action", "preview")
        if action == "orientation":
            frame_orientation = "portrait" if frame_orientation == "landscape" else "landscape"
            set_frame_orientation(frame_orientation)
            action = "preview"
        try:
            if action == "push":
                process_specific_image(
                    path,
                    dither_method=dither_method,
                    frame_orientation=frame_orientation,
                )
            else:
                generate_preview(
                    path,
                    dither_method=dither_method,
                    frame_orientation=frame_orientation,
                )
        except Exception as exc:
            label = "Push" if action == "push" else "Preview"
            return redirect(url_for("gallery.gallery_index", err=f"{label} failed: {format_user_error(exc)}"))
        params = {
            "filename": filename,
            "generated": 1,
            "method": dither_method,
            "orientation": frame_orientation,
        }
        if action == "push":
            params["pushed"] = 1
        return redirect(url_for("gallery.gallery_view", **params))

    show_dithered = request.args.get("generated") == "1"
    if show_dithered:
        dither_method = request.args.get("method", dither_method)
        if dither_method not in ("floyd_steinberg", "atkinson"):
            dither_method = get_default_dither_method()
        frame_orientation = get_frame_orientation()

    flash = ""
    flash_kind = "ok"
    if request.args.get("pushed") == "1":
        flash = "Pushed to frame. Press the driver wake button to update the display."

    return render_image_view_page(
        source_name=filename,
        original_url=url_for("gallery.gallery_file", filename=filename),
        form_action=url_for("gallery.gallery_view", filename=filename),
        dither_method=dither_method,
        frame_orientation=frame_orientation,
        show_dithered=show_dithered,
        flash=flash,
        flash_kind=flash_kind,
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

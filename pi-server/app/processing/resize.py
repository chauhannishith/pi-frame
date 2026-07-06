"""Resize and crop source images to the e-ink display dimensions."""

from PIL import Image

from processing.focal_crop import resize_smart_focal
from processing.types import DisplayLayout, ResizeMode


def resize_stretch(image: Image.Image, width: int, height: int) -> DisplayLayout:
    """Scale to exact dimensions, ignoring aspect ratio."""
    content = image.resize((width, height), Image.Resampling.LANCZOS)
    return DisplayLayout(content=content, frame_size=(width, height))


def resize_contain(image: Image.Image, width: int, height: int) -> DisplayLayout:
    """Scale to fit inside the target box; white letterbox applied after dithering."""
    src_w, src_h = image.size
    scale = min(width / src_w, height / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    content = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    offset_x = (width - new_w) // 2
    offset_y = (height - new_h) // 2
    return DisplayLayout(
        content=content,
        frame_size=(width, height),
        paste_xy=(offset_x, offset_y),
        pad_color=(255, 255, 255),
    )


def resize_cover(image: Image.Image, width: int, height: int) -> DisplayLayout:
    """Scale to fill the target box, then center-crop (legacy, no face detection)."""
    src_w, src_h = image.size
    scale = max(width / src_w, height / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    left = (new_w - width) // 2
    top = (new_h - height) // 2
    content = resized.crop((left, top, left + width, top + height))
    return DisplayLayout(content=content, frame_size=(width, height))


def resize_for_display(
    image: Image.Image,
    width: int,
    height: int,
    mode: ResizeMode | str = ResizeMode.COVER,
) -> DisplayLayout:
    """
    Resize source image to target display dimensions.

    cover   — orientation-aware face focal crop + adaptive padding (default)
    contain — scale to fit inside, letterbox with white
    stretch — ignore aspect ratio
    """
    mode = ResizeMode(mode)
    src = image.convert("RGB")

    if mode == ResizeMode.STRETCH:
        return resize_stretch(src, width, height)
    if mode == ResizeMode.CONTAIN:
        return resize_contain(src, width, height)
    return resize_smart_focal(src, width, height)

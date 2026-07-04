"""Resize and crop source images to the e-ink display dimensions."""

from PIL import Image

from processing.focal_crop import resize_cover_focal
from processing.types import ResizeMode


def resize_stretch(image: Image.Image, width: int, height: int) -> Image.Image:
    """Scale to exact dimensions, ignoring aspect ratio."""
    return image.resize((width, height), Image.Resampling.LANCZOS)


def resize_contain(image: Image.Image, width: int, height: int) -> Image.Image:
    """Scale to fit inside the target box, letterboxing with white."""
    src_w, src_h = image.size
    scale = min(width / src_w, height / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    offset = ((width - new_w) // 2, (height - new_h) // 2)
    canvas.paste(resized, offset)
    return canvas


def resize_cover(image: Image.Image, width: int, height: int) -> Image.Image:
    """Scale to fill the target box, then center-crop (legacy, no face detection)."""
    src_w, src_h = image.size
    scale = max(width / src_w, height / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))
    resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

    left = (new_w - width) // 2
    top = (new_h - height) // 2
    return resized.crop((left, top, left + width, top + height))


def resize_for_display(
    image: Image.Image,
    width: int,
    height: int,
    mode: ResizeMode | str = ResizeMode.COVER,
) -> Image.Image:
    """
    Resize source image to target display dimensions.

    cover   — cover-scale + face-aware vertical crop (default for photos)
    contain — scale to fit inside, letterbox with white
    stretch — ignore aspect ratio
    """
    mode = ResizeMode(mode)
    src = image.convert("RGB")

    if mode == ResizeMode.STRETCH:
        return resize_stretch(src, width, height)
    if mode == ResizeMode.CONTAIN:
        return resize_contain(src, width, height)
    return resize_cover_focal(src, width, height)

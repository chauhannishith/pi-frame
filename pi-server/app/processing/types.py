from dataclasses import dataclass
from enum import Enum
from typing import Literal

from PIL import Image

DitherMethod = Literal["floyd_steinberg", "atkinson", "nearest"]
PackMode = Literal["byte", "packed"]


@dataclass(frozen=True)
class DisplayLayout:
    """
    Aspect-preserved content ready for dithering, plus where/how to letterbox onto the frame.

    Padding is applied after dithering — only `content` is quantized.
    """

    content: Image.Image
    frame_size: tuple[int, int]
    paste_xy: tuple[int, int] = (0, 0)
    pad_color: tuple[int, int, int] = (0, 0, 0)

    @property
    def size(self):
        return self.frame_size

    def composite_rgb(self) -> Image.Image:
        """Undithered full-frame preview (content pasted onto pad color)."""
        canvas = Image.new("RGB", self.frame_size, self.pad_color)
        canvas.paste(self.content, self.paste_xy)
        return canvas

    def getpixel(self, xy):
        return self.composite_rgb().getpixel(xy)


class ResizeMode(str, Enum):
    COVER = "cover"
    CONTAIN = "contain"
    STRETCH = "stretch"

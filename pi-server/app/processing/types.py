from enum import Enum
from typing import Literal

DitherMethod = Literal["floyd_steinberg", "atkinson", "nearest"]
PackMode = Literal["byte", "packed"]


class ResizeMode(str, Enum):
    COVER = "cover"
    CONTAIN = "contain"
    STRETCH = "stretch"

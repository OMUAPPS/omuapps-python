from typing import List, NotRequired, TypedDict

from .accessibility import Accessibility


class Thumbnail(TypedDict):
    url: str
    width: int
    height: int


class Thumbnails(TypedDict):
    thumbnails: List[Thumbnail]


class Image(TypedDict):
    thumbnails: List[Thumbnail]
    accessibility: NotRequired[Accessibility]

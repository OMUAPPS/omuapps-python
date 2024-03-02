from __future__ import annotations

from typing import NotRequired, TypedDict


class TableConfig(TypedDict):
    cache_size: NotRequired[int]

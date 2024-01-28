from __future__ import annotations

import abc
import json as _json
from pathlib import Path
from typing import Dict, List

type Json = str | int | float | bool | None | Dict[str, Json] | List[Json]


class json:
    @staticmethod
    def loads(data: str) -> Json:
        return _json.loads(data)

    @staticmethod
    def dumps(data: Json) -> str:
        return _json.dumps(data, ensure_ascii=False)


class TableAdapter(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def create(cls, path: Path) -> TableAdapter:
        pass

    @abc.abstractmethod
    async def store(self):
        pass

    @abc.abstractmethod
    async def load(self):
        pass

    @abc.abstractmethod
    async def get(self, key: str) -> Json | None:
        pass

    @abc.abstractmethod
    async def get_all(self, keys: List[str]) -> Dict[str, Json]:
        pass

    @abc.abstractmethod
    async def set(self, key: str, value: Json) -> None:
        pass

    @abc.abstractmethod
    async def set_all(self, items: Dict[str, Json]) -> None:
        pass

    @abc.abstractmethod
    async def remove(self, key: str) -> None:
        pass

    @abc.abstractmethod
    async def remove_all(self, keys: List[str]) -> None:
        pass

    @abc.abstractmethod
    async def fetch(
        self, before: int | None, after: str | None, cursor: str | None
    ) -> Dict[str, Json]:
        pass

    @abc.abstractmethod
    async def first(self) -> str | None:
        pass

    @abc.abstractmethod
    async def last(self) -> str | None:
        pass

    @abc.abstractmethod
    async def clear(self) -> None:
        pass

    @abc.abstractmethod
    async def size(self) -> int:
        pass

from __future__ import annotations

import abc
from pathlib import Path
from typing import Dict, List


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
    async def get(self, key: str) -> bytes | None:
        pass

    @abc.abstractmethod
    async def get_all(self, keys: List[str]) -> Dict[str, bytes]:
        pass

    @abc.abstractmethod
    async def set(self, key: str, value: bytes) -> None:
        pass

    @abc.abstractmethod
    async def set_all(self, items: Dict[str, bytes]) -> None:
        pass

    @abc.abstractmethod
    async def remove(self, key: str) -> None:
        pass

    @abc.abstractmethod
    async def remove_all(self, keys: List[str]) -> None:
        pass

    @abc.abstractmethod
    async def fetch_items(
        self, before: int | None, after: str | None, cursor: str | None
    ) -> Dict[str, bytes]:
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

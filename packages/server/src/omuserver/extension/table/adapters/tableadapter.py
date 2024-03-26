from __future__ import annotations

import abc
from pathlib import Path
from typing import Dict, List, Mapping


class TableAdapter(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def create(cls, path: Path) -> TableAdapter: ...

    @abc.abstractmethod
    async def store(self): ...

    @abc.abstractmethod
    async def load(self): ...

    @abc.abstractmethod
    async def get(self, key: str) -> bytes | None: ...

    @abc.abstractmethod
    async def get_all(self, keys: List[str]) -> Dict[str, bytes]: ...

    @abc.abstractmethod
    async def set(self, key: str, value: bytes) -> None: ...

    @abc.abstractmethod
    async def set_all(self, items: Mapping[str, bytes]) -> None: ...

    @abc.abstractmethod
    async def remove(self, key: str) -> None: ...

    @abc.abstractmethod
    async def remove_all(self, keys: List[str]) -> None: ...

    @abc.abstractmethod
    async def fetch_items(
        self, before: int | None, after: int | None, cursor: str | None
    ) -> Dict[str, bytes]: ...

    @abc.abstractmethod
    async def fetch_all(self) -> Dict[str, bytes]: ...

    @abc.abstractmethod
    async def first(self) -> str | None: ...

    @abc.abstractmethod
    async def last(self) -> str | None: ...

    @abc.abstractmethod
    async def clear(self) -> None: ...

    @abc.abstractmethod
    async def size(self) -> int: ...

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, AsyncIterator, Dict, List, Union

if TYPE_CHECKING:
    from omuserver.session import Session
    from omu.extension.table import TableConfig
    from .adapters.tableadapter import TableAdapter

type Json = Union[str, int, float, bool, None, Dict[str, Json], List[Json]]


class ServerTable(abc.ABC):
    @property
    @abc.abstractmethod
    def cache(self) -> Dict[str, bytes]:
        ...

    @abc.abstractmethod
    def set_config(self, config: TableConfig) -> None:
        ...

    @property
    @abc.abstractmethod
    def adapter(self) -> TableAdapter | None:
        ...

    @abc.abstractmethod
    def set_adapter(self, adapter: TableAdapter) -> None:
        ...

    @abc.abstractmethod
    def attach_session(self, session: Session) -> None:
        ...

    @abc.abstractmethod
    def detach_session(self, session: Session) -> None:
        ...

    @abc.abstractmethod
    def attach_proxy_session(self, session: Session) -> None:
        ...

    @abc.abstractmethod
    async def proxy(self, session: Session, key: int, items: Dict[str, bytes]) -> int:
        ...

    @abc.abstractmethod
    async def store(self) -> None:
        ...

    @abc.abstractmethod
    async def get(self, key: str) -> bytes | None:
        ...

    @abc.abstractmethod
    async def get_all(self, keys: List[str]) -> Dict[str, bytes]:
        ...

    @abc.abstractmethod
    async def add(self, items: Dict[str, bytes]) -> None:
        ...

    @abc.abstractmethod
    async def update(self, items: Dict[str, bytes]) -> None:
        ...

    @abc.abstractmethod
    async def remove(self, keys: List[str]) -> None:
        ...

    @abc.abstractmethod
    async def clear(self) -> None:
        ...

    @abc.abstractmethod
    async def fetch_items(
        self,
        before: int | None = None,
        after: int | None = None,
        cursor: str | None = None,
    ) -> Dict[str, bytes]:
        ...

    @abc.abstractmethod
    async def iterate(self) -> AsyncIterator[bytes]:
        ...

    @abc.abstractmethod
    async def size(self) -> int:
        ...

    @abc.abstractmethod
    def add_listener(self, listener: ServerTableListener) -> None:
        ...

    @abc.abstractmethod
    def remove_listener(self, listener: ServerTableListener) -> None:
        ...


class ServerTableListener:
    async def on_add(self, items: Dict[str, bytes]) -> None:
        ...

    async def on_update(self, items: Dict[str, bytes]) -> None:
        ...

    async def on_remove(self, items: Dict[str, bytes]) -> None:
        ...

    async def on_clear(self) -> None:
        ...

    async def on_cache_update(self, cache: Dict[str, bytes]) -> None:
        ...

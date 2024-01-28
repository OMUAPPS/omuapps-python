from __future__ import annotations

import abc
from typing import TYPE_CHECKING, AsyncIterator, Dict, List, Union

if TYPE_CHECKING:
    from omu.interface import Serializable

    from omuserver.session import Session

type Json = Union[str, int, float, bool, None, Dict[str, Json], List[Json]]


class ServerTable[T](abc.ABC):
    @property
    @abc.abstractmethod
    def serializer(self) -> Serializable[T, Json]:
        ...

    @property
    @abc.abstractmethod
    def cache(self) -> Dict[str, T]:
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
    async def proxy(self, session: Session, key: int, items: Dict[str, T]) -> int:
        ...

    @abc.abstractmethod
    async def store(self) -> None:
        ...

    @abc.abstractmethod
    async def load(self) -> None:
        ...

    @abc.abstractmethod
    async def get(self, key: str) -> T | None:
        ...

    @abc.abstractmethod
    async def get_all(self, keys: List[str]) -> Dict[str, T]:
        ...

    @abc.abstractmethod
    async def add(self, items: Dict[str, T]) -> None:
        ...

    @abc.abstractmethod
    async def update(self, items: Dict[str, T]) -> None:
        ...

    @abc.abstractmethod
    async def remove(self, items: List[str]) -> None:
        ...

    @abc.abstractmethod
    async def clear(self) -> None:
        ...

    @abc.abstractmethod
    async def fetch(
        self,
        before: int | None = None,
        after: int | None = None,
        cursor: str | None = None,
    ) -> Dict[str, T]:
        ...

    @abc.abstractmethod
    async def iterator(self) -> AsyncIterator[T]:
        ...

    @abc.abstractmethod
    async def size(self) -> int:
        ...

    @abc.abstractmethod
    def add_listener(self, listener: TableListener[T]) -> None:
        ...

    @abc.abstractmethod
    def remove_listener(self, listener: TableListener[T]) -> None:
        ...


class TableListener[T]:
    async def on_add(self, items: Dict[str, T]) -> None:
        ...

    async def on_update(self, items: Dict[str, T]) -> None:
        ...

    async def on_remove(self, items: Dict[str, T]) -> None:
        ...

    async def on_clear(self) -> None:
        ...

    async def on_cache_update(self, cache: Dict[str, T]) -> None:
        ...

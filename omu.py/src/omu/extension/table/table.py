from __future__ import annotations

import abc
from typing import AsyncGenerator, Awaitable, Callable, Dict, Protocol

from omu.extension.extension import ExtensionType
from omu.extension.server.model.app import App
from omu.extension.table.model.table_info import TableInfo
from omu.interface import Keyable, Serializable
from omu.interface.serializable import Serializer

type AsyncCallback[**P] = Callable[P, Awaitable]
type Coro[**P, T] = Callable[P, Awaitable[T]]


class Table[T: Keyable](abc.ABC):
    @property
    @abc.abstractmethod
    def cache(self) -> Dict[str, T]:
        ...

    @abc.abstractmethod
    async def get(self, key: str) -> T | None:
        ...

    @abc.abstractmethod
    async def add(self, *items: T) -> None:
        ...

    @abc.abstractmethod
    async def update(self, *items: T) -> None:
        ...

    @abc.abstractmethod
    async def remove(self, *items: T) -> None:
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
    async def iter(
        self,
        backward: bool = False,
        cursor: str | None = None,
    ) -> AsyncGenerator[T, None]:
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

    @abc.abstractmethod
    def listen(self, listener: AsyncCallback[Dict[str, T]] | None = None) -> None:
        ...

    @abc.abstractmethod
    def proxy(self, callback: Coro[[T], T | None]) -> Callable[[], None]:
        ...


class TableListener[T: Keyable]:
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


class CallbackTableListener[T: Keyable](TableListener[T]):
    def __init__(
        self,
        on_add: AsyncCallback[Dict[str, T]] | None = None,
        on_update: AsyncCallback[Dict[str, T]] | None = None,
        on_remove: AsyncCallback[Dict[str, T]] | None = None,
        on_clear: AsyncCallback[[]] | None = None,
        on_cache_update: AsyncCallback[Dict[str, T]] | None = None,
    ):
        self._on_add = on_add
        self._on_update = on_update
        self._on_remove = on_remove
        self._on_clear = on_clear
        self._on_cache_update = on_cache_update

    async def on_add(self, items: Dict[str, T]) -> None:
        if self._on_add:
            await self._on_add(items)

    async def on_update(self, items: Dict[str, T]) -> None:
        if self._on_update:
            await self._on_update(items)

    async def on_remove(self, items: Dict[str, T]) -> None:
        if self._on_remove:
            await self._on_remove(items)

    async def on_clear(self) -> None:
        if self._on_clear:
            await self._on_clear()

    async def on_cache_update(self, cache: Dict[str, T]) -> None:
        if self._on_cache_update:
            await self._on_cache_update(cache)


class TableType[T: Keyable, D](abc.ABC):
    @property
    @abc.abstractmethod
    def info(self) -> TableInfo:
        ...

    @property
    @abc.abstractmethod
    def serializer(self) -> Serializable[T, D]:
        ...


class TableEntry[T: Keyable, D](Protocol):
    def key(self) -> str:
        ...

    def to_json(self) -> D:
        ...

    @classmethod
    def from_json(cls, json: D) -> T:
        ...


class ModelTableType[T: Keyable, D](TableType[T, D]):
    def __init__(self, info: TableInfo, serializer: Serializable[T, D]):
        self._info = info
        self._serializer = serializer

    @classmethod
    def of[_T: Keyable, _D](
        cls, app: App, name: str, model: type[TableEntry[_T, _D]]
    ) -> TableType[_T, _D]:
        return ModelTableType(
            info=TableInfo.of(app, name),
            serializer=Serializer.model(model),
        )

    @classmethod
    def of_extension[_T: Keyable, _D](
        cls, extension: ExtensionType, name: str, model: type[TableEntry[_T, _D]]
    ) -> TableType[_T, _D]:
        return ModelTableType(
            info=TableInfo.of_extension(extension, name),
            serializer=Serializer.model(model),
        )

    @property
    def info(self) -> TableInfo:
        return self._info

    @property
    def key(self) -> str:
        return self._info.key()

    @property
    def serializer(self) -> Serializable[T, D]:
        return self._serializer

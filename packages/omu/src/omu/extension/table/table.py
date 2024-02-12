from __future__ import annotations

import abc
from typing import AsyncGenerator, Callable, Dict, Mapping

from omu.extension import ExtensionType
from omu.extension.server import App
from omu.helper import AsyncCallback, Coro
from omu.identifier import Identifier
from omu.interface import Jsonable, Keyable, Serializable, Serializer

from .table_info import TableInfo


class Table[T: Keyable](abc.ABC):
    @property
    @abc.abstractmethod
    def cache(self) -> Mapping[str, T]:
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
    async def fetch_items(
        self,
        before: int | None = None,
        after: int | None = None,
        cursor: str | None = None,
    ) -> Mapping[str, T]:
        ...

    @abc.abstractmethod
    async def iterate(
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
    _on_add = None
    _on_update = None
    _on_remove = None
    _on_clear = None
    _on_cache_update = None

    def __init__(
        self,
        on_add: AsyncCallback[Mapping[str, T]] | None = None,
        on_update: AsyncCallback[Mapping[str, T]] | None = None,
        on_remove: AsyncCallback[Mapping[str, T]] | None = None,
        on_clear: AsyncCallback[[]] | None = None,
        on_cache_update: AsyncCallback[Mapping[str, T]] | None = None,
    ):
        self._on_add = on_add
        self._on_update = on_update
        self._on_remove = on_remove
        self._on_clear = on_clear
        self._on_cache_update = on_cache_update

    async def on_add(self, items: Mapping[str, T]) -> None:
        if self._on_add:
            await self._on_add(items)

    async def on_update(self, items: Mapping[str, T]) -> None:
        if self._on_update:
            await self._on_update(items)

    async def on_remove(self, items: Mapping[str, T]) -> None:
        if self._on_remove:
            await self._on_remove(items)

    async def on_clear(self) -> None:
        if self._on_clear:
            await self._on_clear()

    async def on_cache_update(self, cache: Mapping[str, T]) -> None:
        if self._on_cache_update:
            await self._on_cache_update(cache)


class TableType[T: Keyable](abc.ABC):
    @property
    @abc.abstractmethod
    def info(self) -> TableInfo:
        ...

    @property
    @abc.abstractmethod
    def serializer(self) -> Serializable[T, bytes]:
        ...


type ModelEntry[T: Keyable, D] = Jsonable[T, D]


class ModelTableType[T: Keyable, D](TableType[T]):
    def __init__(self, info: TableInfo, model: type[ModelEntry[T, D]]):
        self._info = info
        self._serializer = Serializer.model(model).pipe(Serializer.json())

    @classmethod
    def of[_T: Keyable, _D](
        cls, app: App, name: str, model: type[ModelEntry[_T, _D]]
    ) -> ModelTableType[_T, _D]:
        return ModelTableType(
            info=TableInfo.of(Identifier.create(app.key(), name)),
            model=model,
        )

    @classmethod
    def of_extension[_T: Keyable, _D](
        cls, extension: ExtensionType, name: str, model: type[ModelEntry[_T, _D]]
    ) -> ModelTableType[_T, _D]:
        return ModelTableType(
            info=TableInfo.of(Identifier.create(extension.key, name)),
            model=model,
        )

    @property
    def info(self) -> TableInfo:
        return self._info

    @property
    def key(self) -> str:
        return self._info.key()

    @property
    def serializer(self) -> Serializable[T, bytes]:
        return self._serializer

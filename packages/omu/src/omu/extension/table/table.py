from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    AsyncGenerator,
    Callable,
    Dict,
    Mapping,
    NotRequired,
    TypedDict,
)

from omu.identifier import Identifier
from omu.interface import Keyable
from omu.serializer import Serializer

if TYPE_CHECKING:
    from omu.helper import AsyncCallback, Coro
    from omu.serializer import JsonSerializable, Serializable


class TableConfig(TypedDict):
    cache_size: NotRequired[int]


class Table[T](abc.ABC):
    @property
    @abc.abstractmethod
    def cache(self) -> Mapping[str, T]: ...

    @abc.abstractmethod
    def set_cache_size(self, size: int) -> None: ...

    @abc.abstractmethod
    async def get(self, key: str) -> T | None: ...

    @abc.abstractmethod
    async def add(self, *items: T) -> None: ...

    @abc.abstractmethod
    async def update(self, *items: T) -> None: ...

    @abc.abstractmethod
    async def remove(self, *items: T) -> None: ...

    @abc.abstractmethod
    async def clear(self) -> None: ...

    @abc.abstractmethod
    async def fetch_items(
        self,
        before: int | None = None,
        after: int | None = None,
        cursor: str | None = None,
    ) -> Mapping[str, T]: ...

    @abc.abstractmethod
    async def iterate(
        self,
        backward: bool = False,
        cursor: str | None = None,
    ) -> AsyncGenerator[T, None]: ...

    @abc.abstractmethod
    async def size(self) -> int: ...

    @abc.abstractmethod
    def listen(self, listener: AsyncCallback[Dict[str, T]] | None = None) -> None: ...

    @abc.abstractmethod
    def proxy(self, callback: Coro[[T], T | None]) -> Callable[[], None]: ...

    @abc.abstractmethod
    def set_config(self, config: TableConfig) -> None: ...

    @abc.abstractmethod
    def add_listener(self, listener: TableListener[T]) -> None: ...

    @abc.abstractmethod
    def remove_listener(self, listener: TableListener[T]) -> None: ...


class TableListener[T]:
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


type ModelEntry[T: Keyable, D] = JsonSerializable[T, D]


@dataclass(frozen=True)
class TableType[T]:
    identifier: Identifier
    serializer: Serializable[T, bytes]
    key_func: Callable[[T], str]

    @classmethod
    def create_model[_T: Keyable, _D](
        cls,
        identifier: Identifier,
        name: str,
        model: type[ModelEntry[_T, _D]],
    ) -> TableType[_T]:
        return TableType(
            identifier=identifier / name,
            serializer=Serializer.model(model).pipe(Serializer.json()),
            key_func=lambda item: item.key(),
        )

    @classmethod
    def create_serialized[_T: Keyable](
        cls,
        identifier: Identifier,
        name: str,
        serializer: Serializable[_T, bytes],
    ) -> TableType[_T]:
        return TableType(
            identifier=identifier / name,
            serializer=serializer,
            key_func=lambda item: item.key(),
        )

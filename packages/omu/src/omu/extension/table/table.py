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

from omu.event_emitter import EventEmitter
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
    async def fetch_all(self) -> Dict[str, T]: ...

    @abc.abstractmethod
    async def iterate(
        self,
        backward: bool = False,
        cursor: str | None = None,
    ) -> AsyncGenerator[T, None]: ...

    @abc.abstractmethod
    async def size(self) -> int: ...

    @abc.abstractmethod
    def listen(
        self, listener: AsyncCallback[Mapping[str, T]] | None = None
    ) -> Callable[[], None]: ...

    @abc.abstractmethod
    def proxy(self, callback: Coro[[T], T | None]) -> Callable[[], None]: ...

    @abc.abstractmethod
    def set_config(self, config: TableConfig) -> None: ...

    @property
    @abc.abstractmethod
    def listeners(self) -> TableListeners[T]: ...


class TableListeners[T]:
    def __init__(
        self,
        table: Table[T],
    ) -> None:
        self.unlisten: Callable[[], None] | None = None

        def listen():
            self.unlisten = table.listen()

        def unlisten():
            if self.unlisten:
                self.unlisten()

        self.add: EventEmitter[Mapping[str, T]] = EventEmitter(
            on_subscribe=listen, on_empty=unlisten
        )
        self.update: EventEmitter[Mapping[str, T]] = EventEmitter(
            on_subscribe=listen, on_empty=unlisten
        )
        self.remove: EventEmitter[Mapping[str, T]] = EventEmitter(
            on_subscribe=listen, on_empty=unlisten
        )
        self.clear: EventEmitter[[]] = EventEmitter(
            on_subscribe=listen, on_empty=unlisten
        )
        self.cache_update: EventEmitter[Mapping[str, T]] = EventEmitter(
            on_subscribe=listen, on_empty=unlisten
        )


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

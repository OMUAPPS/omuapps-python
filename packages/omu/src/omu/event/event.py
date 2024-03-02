from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List

from omu.serializer import Serializer

if TYPE_CHECKING:
    from omu.extension.extension import ExtensionType
    from omu.extension.server import App
    from omu.serializer import Serializable


@dataclass
class EventData:
    type: str
    data: bytes


class EventType[T](abc.ABC):
    @property
    @abc.abstractmethod
    def type(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def serializer(self) -> Serializable[T, bytes]:
        ...

    def __str__(self) -> str:
        return self.type

    def __repr__(self) -> str:
        return self.type


type Jsonable = str | int | float | bool | None | Dict[str, Jsonable] | List[Jsonable]


class JsonEventType[T](EventType[T]):
    def __init__(
        self, owner: str, name: str, serializer: Serializable[T, Any] | None = None
    ):
        self._type = f"{owner}:{name}"
        self._serializer = (
            Serializer.noop()
            .pipe(serializer or Serializer.noop())
            .pipe(Serializer.json())
        )

    @property
    def type(self) -> str:
        return self._type

    @property
    def serializer(self) -> Serializable[T, bytes]:
        return self._serializer

    @classmethod
    def of(cls, app: App, name: str) -> JsonEventType[T]:
        return cls(
            owner=app.key(),
            name=name,
            serializer=Serializer.noop(),
        )

    @classmethod
    def of_extension(
        cls,
        extension: ExtensionType,
        name: str,
        serializer: Serializable[T, Any] | None = None,
    ) -> JsonEventType[T]:
        return cls(
            owner=extension.name,
            name=name,
            serializer=serializer,
        )


class SerializeEventType[T](EventType[T]):
    def __init__(self, owner: str, name: str, serializer: Serializable[T, bytes]):
        self._type = f"{owner}:{name}"
        self._serializer = serializer

    @property
    def type(self) -> str:
        return self._type

    @property
    def serializer(self) -> Serializable[T, bytes]:
        return self._serializer

    @classmethod
    def of(
        cls, app: App, name: str, serializer: Serializable[T, bytes]
    ) -> SerializeEventType[T]:
        return cls(
            owner=app.key(),
            name=name,
            serializer=serializer,
        )

    @classmethod
    def of_extension(
        cls, extension: ExtensionType, name: str, serializer: Serializable[T, bytes]
    ) -> SerializeEventType[T]:
        return cls(
            owner=extension.name,
            name=name,
            serializer=serializer,
        )

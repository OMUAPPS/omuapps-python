from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any, Dict, List, TypedDict

from omu.interface.serializable import Serializer

if TYPE_CHECKING:
    from omu.extension.extension import ExtensionType
    from omu.extension.server.model.app import App
    from omu.interface import Serializable


class EventData:
    def __init__(self, type: str, data: bytes):
        self.type = type
        self.data = data

    @classmethod
    def from_json_as[T](cls, event: EventType[T], data: Any) -> T:
        if "type" not in data:
            raise ValueError("Missing type field in event json")
        if data["type"] != event.type:
            raise ValueError(f"Expected type {event.type} but got {data['type']}")
        if "data" not in data:
            raise ValueError("Missing data field in event json")
        return event.serializer.deserialize(data["data"])

    def __str__(self) -> str:
        return f"{self.type}:{self.data}"

    def __repr__(self) -> str:
        return f"{self.type}:{self.data}"


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


type Jsonable = (
    str | int | float | bool | None | Dict[str, Jsonable] | List[Jsonable] | TypedDict
)


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
            owner=extension.key,
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
            owner=extension.key,
            name=name,
            serializer=serializer,
        )

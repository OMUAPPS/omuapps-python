from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Dict, List, TypedDict

from omu.interface.serializable import Serializer

if TYPE_CHECKING:
    from omu.extension.extension import ExtensionType
    from omu.extension.server.model.app import App
    from omu.interface import Serializable


class EventJson[T]:
    def __init__(self, type: str, data: T):
        self.type = type
        self.data = data

    @classmethod
    def from_json(cls, json: dict) -> EventJson[T]:
        if "type" not in json:
            raise ValueError("Missing type field in event json")
        if "data" not in json:
            raise ValueError("Missing data field in event json")
        return cls(**json)

    @classmethod
    def from_json_as[_T, _D](cls, event: EventType[_T, _D], data: dict) -> _T:
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


class EventType[T, D](abc.ABC):
    @property
    @abc.abstractmethod
    def type(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def serializer(self) -> Serializable[T, D]:
        ...

    def __str__(self) -> str:
        return self.type

    def __repr__(self) -> str:
        return self.type


type Jsonable = (
    str | int | float | bool | None | Dict[str, Jsonable] | List[Jsonable] | TypedDict
)


class JsonEventType[T: Jsonable](EventType[T, T]):
    def __init__(self, owner: str, name: str, serializer: Serializable[T, T]):
        self._type = f"{owner}:{name}"
        self._serializer = serializer

    @property
    def type(self) -> str:
        return self._type

    @property
    def serializer(self) -> Serializable[T, T]:
        return self._serializer

    @classmethod
    def of(cls, app: App, name: str) -> JsonEventType[T]:
        return cls(
            owner=app.key(),
            name=name,
            serializer=Serializer.noop(),
        )

    @classmethod
    def of_extension(cls, extension: ExtensionType, name: str) -> JsonEventType[T]:
        return cls(
            owner=extension.key,
            name=name,
            serializer=Serializer.noop(),
        )


class SerializeEventType[T, D](EventType[T, D]):
    def __init__(self, owner: str, name: str, serializer: Serializable[T, D]):
        self._type = f"{owner}:{name}"
        self._serializer = serializer

    @property
    def type(self) -> str:
        return self._type

    @property
    def serializer(self) -> Serializable[T, D]:
        return self._serializer

    @classmethod
    def of(
        cls, app: App, name: str, serializer: Serializable[T, D]
    ) -> SerializeEventType[T, D]:
        return cls(
            owner=app.key(),
            name=name,
            serializer=serializer,
        )

    @classmethod
    def of_extension(
        cls, extension: ExtensionType, name: str, serializer: Serializable[T, D]
    ) -> SerializeEventType[T, D]:
        return cls(
            owner=extension.key,
            name=name,
            serializer=serializer,
        )

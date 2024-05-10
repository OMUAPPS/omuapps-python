from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from omu.identifier import Identifier
from omu.serializer import Serializable, Serializer


@dataclass(frozen=True)
class PacketData:
    type: str
    data: bytes


@dataclass(frozen=True)
class Packet[T]:
    type: PacketType[T]
    data: T


class PacketClass[T](Protocol):
    def serialize(self, item: T) -> bytes: ...

    def deserialize(self, item: bytes) -> T: ...


@dataclass(frozen=True)
class PacketType[T]:
    id: Identifier
    serializer: Serializable[T, bytes]

    @classmethod
    def create_json[_T](
        cls,
        identifier: Identifier,
        name: str,
        serializer: Serializable[_T, Any] | None = None,
    ) -> PacketType[_T]:
        return PacketType(
            id=identifier / name,
            serializer=Serializer.of(serializer or Serializer.noop()).to_json(),
        )

    @classmethod
    def create_serialized[_T](
        cls,
        identifier: Identifier,
        name: str,
        serializer: Serializable[_T, bytes],
    ) -> PacketType[_T]:
        return PacketType(
            id=identifier / name,
            serializer=serializer,
        )

    @classmethod
    def create[_T](
        cls,
        identifier: Identifier,
        name: str,
        type_class: PacketClass[_T],
    ) -> PacketType[_T]:
        return PacketType(
            id=identifier / name,
            serializer=type_class,
        )

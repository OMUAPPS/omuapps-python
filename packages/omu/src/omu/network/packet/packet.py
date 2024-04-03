from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from omu.identifier import Identifier
from omu.serializer import Serializer

if TYPE_CHECKING:
    from omu.serializer import Serializable


@dataclass(frozen=True)
class PacketData:
    type: str
    data: bytes


@dataclass(frozen=True)
class Packet[T]:
    type: PacketType[T]
    data: T


@dataclass(frozen=True)
class PacketType[T]:
    identifier: Identifier
    serializer: Serializable[T, bytes]

    @classmethod
    def create_json[_T](
        cls,
        identifier: Identifier,
        name: str,
        serializer: Serializable[_T, Any] | None = None,
    ) -> PacketType[_T]:
        return PacketType(
            identifier=identifier / name,
            serializer=Serializer.of(serializer or Serializer.noop()).pipe(
                Serializer.json()
            ),
        )

    @classmethod
    def create_serialized[_T](
        cls,
        identifier: Identifier,
        name: str,
        serializer: Serializable[_T, bytes],
    ) -> PacketType[_T]:
        return PacketType(
            identifier=identifier / name,
            serializer=serializer,
        )

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from omu.identifier import Identifier
from omu.serializer import Serializer

if TYPE_CHECKING:
    from omu.serializer import Serializable


@dataclass
class PacketData:
    type: Final[str]
    data: Final[bytes]


@dataclass
class Packet[T]:
    type: Final[PacketType[T]]
    data: Final[T]


@dataclass
class PacketType[T]:
    identifier: Final[Identifier]
    serializer: Final[Serializable[T, bytes]]

    @classmethod
    def create_json[_T](
        cls,
        identifier: Identifier,
        name: str,
        serializer: Serializable[_T, Any] = Serializer.noop(),
    ) -> PacketType[_T]:
        return PacketType(
            identifier=identifier / name,
            serializer=Serializer.of(serializer).pipe(Serializer.json()),
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

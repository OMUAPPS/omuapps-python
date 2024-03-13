from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Dict

from omu.identifier import Identifier
from omu.network.packet.packet import Packet, PacketData, PacketType

if TYPE_CHECKING:
    from omu.network.network import Network


class PacketMapper:
    def __init__(self) -> None:
        self._mappers: Dict[Identifier, PacketType] = {}

    def register(self, *packet_types: PacketType) -> None:
        for packet_type in packet_types:
            if self._mappers.get(packet_type.identifier):
                raise ValueError(
                    f"Packet id {packet_type.identifier} already registered"
                )
            self._mappers[packet_type.identifier] = packet_type

    def serialize(self, packet: Packet) -> PacketData:
        return PacketData(
            type=packet.packet_type.identifier.key(),
            data=packet.packet_type.serializer.serialize(packet.packet_data),
        )

    def deserialize(self, data: PacketData) -> Packet:
        identifier = Identifier.from_key(data.type)
        packet_type = self._mappers.get(identifier)
        if not packet_type:
            raise ValueError(f"Unknown packet type {data.type}")
        return Packet(
            packet_type=packet_type,
            packet_data=packet_type.serializer.deserialize(data.data),
        )


class Connection(abc.ABC):
    @abc.abstractmethod
    async def connect(self) -> Network: ...

    @abc.abstractmethod
    async def receive(self, serializer: PacketMapper) -> Packet: ...

    @abc.abstractmethod
    async def send(self, packet: Packet, serializer: PacketMapper) -> None: ...

    @abc.abstractmethod
    async def close(self) -> None: ...

    @property
    @abc.abstractmethod
    def closed(self) -> bool: ...

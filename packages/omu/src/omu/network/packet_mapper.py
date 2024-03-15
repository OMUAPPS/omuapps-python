from typing import Dict

from omu.identifier import Identifier
from omu.serializer import Serializable

from .packet import Packet, PacketData, PacketType


class PacketMapper(Serializable[Packet, PacketData]):
    def __init__(self) -> None:
        self._map: Dict[Identifier, PacketType] = {}

    def register(self, *packet_types: PacketType) -> None:
        for packet_type in packet_types:
            if self._map.get(packet_type.identifier):
                raise ValueError(
                    f"Packet id {packet_type.identifier} already registered"
                )
            self._map[packet_type.identifier] = packet_type

    def serialize(self, packet: Packet) -> PacketData:
        return PacketData(
            type=packet.type.identifier.key(),
            data=packet.type.serializer.serialize(packet.data),
        )

    def deserialize(self, data: PacketData) -> Packet:
        identifier = Identifier.from_key(data.type)
        packet_type = self._map.get(identifier)
        if not packet_type:
            raise ValueError(f"Packet type {identifier} not registered")
        return Packet(
            type=packet_type,
            data=packet_type.serializer.deserialize(data.data),
        )
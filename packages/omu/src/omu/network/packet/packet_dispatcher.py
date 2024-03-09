from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict

from loguru import logger

from omu.event_emitter import EventEmitter
from omu.helper import Coro

if TYPE_CHECKING:
    from omu.network.connection import Connection
    from omu.network.packet import PacketData, PacketType


class PacketDispatcher:
    def __init__(self, connection: Connection):
        self._packet_listeners: Dict[str, PacketListeners] = {}
        connection.listeners.packet += self.process_packet

    def register(self, *packet_types: PacketType) -> None:
        for packet_type in packet_types:
            if self._packet_listeners.get(packet_type.type):
                raise ValueError(f"Event type {packet_type.type} already registered")
            self._packet_listeners[packet_type.type] = PacketListeners(packet_type)

    def add_packet_handler[T](
        self,
        packet_type: PacketType[T],
        packet_handler: Coro[[T], None] | None = None,
    ):
        if not self._packet_listeners.get(packet_type.type):
            raise ValueError(f"Event type {packet_type.type} not registered")

        def decorator(packet_handler: Coro[[T], None]) -> None:
            self._packet_listeners[packet_type.type].listeners += packet_handler

        if packet_handler:
            decorator(packet_handler)
        return decorator

    async def process_packet(self, packet_data: PacketData) -> None:
        event = self._packet_listeners.get(packet_data.type)
        if not event:
            logger.warning(f"Received unknown event type {packet_data.type}")
            return
        data = event.event_type.serializer.deserialize(packet_data.data)
        await event.listeners.emit(data)


@dataclass
class PacketListeners[T]:
    event_type: PacketType[T]
    listeners: EventEmitter[T] = field(default_factory=EventEmitter)

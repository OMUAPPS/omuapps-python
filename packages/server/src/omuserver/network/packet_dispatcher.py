from __future__ import annotations
from dataclasses import dataclass, field

from typing import TYPE_CHECKING, Callable, Dict

from loguru import logger
from omuserver.network.network import Network

from omuserver.session import Session
from omu.event_emitter import EventEmitter

if TYPE_CHECKING:
    from omu.network.packet import PacketData, PacketType
    from omu.helper import Coro


class ServerPacketDispatcher:
    def __init__(self, network: Network):
        self._packet_listeners: Dict[str, PacketListeners] = {}
        network.listeners.connected += self.on_connected

    async def on_connected(self, session: Session) -> None:
        session.listeners.packet += self.process_packet

    async def process_packet(self, session: Session, packet_data: PacketData) -> None:
        packet = self._packet_listeners.get(packet_data.type)
        if not packet:
            logger.warning(f"Received unknown event type {packet_data.type}")
            return
        data = packet.event_type.serializer.deserialize(packet_data.data)
        await packet.listeners.emit(session, data)

    def register(self, *types: PacketType) -> None:
        for type in types:
            if self._packet_listeners.get(type.type):
                raise ValueError(f"Event type {type.type} already registered")
            self._packet_listeners[type.type] = PacketListeners(type)

    def add_packet_handler[T](
        self,
        event_type: PacketType[T],
        listener: Coro[[Session, T], None] | None = None,
    ) -> Callable[[Coro[[Session, T], None]], None]:
        if not self._packet_listeners.get(event_type.type):
            raise ValueError(f"Event type {event_type.type} not registered")

        def decorator(listener: Coro[[Session, T], None]) -> None:
            self._packet_listeners[event_type.type].listeners += listener

        if listener:
            decorator(listener)
        return decorator


@dataclass
class PacketListeners[T]:
    event_type: PacketType[T]
    listeners: EventEmitter[Session, T] = field(default_factory=EventEmitter)

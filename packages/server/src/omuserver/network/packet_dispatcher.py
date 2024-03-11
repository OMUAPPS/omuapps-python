from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Dict

from loguru import logger
from omu.event_emitter import EventEmitter
from omu.network.connection import PacketMapper

from omuserver.session import Session

if TYPE_CHECKING:
    from omu.helper import Coro
    from omu.network.packet import Packet, PacketType


class ServerPacketDispatcher:
    def __init__(self):
        self.packet_mapper = PacketMapper()
        self._packet_listeners: Dict[str, PacketListeners] = {}

    async def process_connection(self, session: Session) -> None:
        session.listeners.packet += self.process_packet

    async def process_packet(self, session: Session, packet: Packet) -> None:
        listeners = self._packet_listeners.get(packet.packet_type.type)
        if not listeners:
            logger.warning(f"Received unknown event type {packet.packet_type}")
            return
        await listeners.listeners.emit(session, packet.packet_data)

    def register(self, *types: PacketType) -> None:
        self.packet_mapper.register(*types)
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

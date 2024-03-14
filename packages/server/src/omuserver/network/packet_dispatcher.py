from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Dict

from loguru import logger
from omu.event_emitter import EventEmitter
from omu.identifier import Identifier
from omu.network.packet_mapper import PacketMapper

from omuserver.session import Session

if TYPE_CHECKING:
    from omu.helper import Coro
    from omu.network.packet import Packet, PacketType


class ServerPacketDispatcher:
    def __init__(self):
        self.packet_mapper = PacketMapper()
        self._packet_listeners: Dict[Identifier, PacketListeners] = {}

    async def process_connection(self, session: Session) -> None:
        session.listeners.packet += self.process_packet

    async def process_packet(self, session: Session, packet: Packet) -> None:
        listeners = self._packet_listeners.get(packet.type.identifier)
        if not listeners:
            logger.warning(f"Received unknown event type {packet.type}")
            return
        await listeners.listeners.emit(session, packet.data)

    def register(self, *types: PacketType) -> None:
        self.packet_mapper.register(*types)
        for type in types:
            if self._packet_listeners.get(type.identifier):
                raise ValueError(f"Event id {type.identifier} already registered")
            self._packet_listeners[type.identifier] = PacketListeners(type)

    def add_packet_handler[T](
        self,
        event_type: PacketType[T],
        listener: Coro[[Session, T], None] | None = None,
    ) -> Callable[[Coro[[Session, T], None]], None]:
        if not self._packet_listeners.get(event_type.identifier):
            raise ValueError(f"Event type {event_type.identifier} not registered")

        def decorator(listener: Coro[[Session, T], None]) -> None:
            self._packet_listeners[event_type.identifier].listeners.subscribe(listener)

        if listener:
            decorator(listener)
        return decorator


@dataclass(frozen=True)
class PacketListeners[T]:
    event_type: PacketType[T]
    listeners: EventEmitter[Session, T] = field(default_factory=EventEmitter)

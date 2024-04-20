from __future__ import annotations

import abc
import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from omu.event_emitter import EventEmitter
from omu.network.packet import PACKET_TYPES, Packet, PacketType
from omu.network.packet.packet_types import ConnectPacket

if TYPE_CHECKING:
    from omu import App
    from omu.network.packet_mapper import PacketMapper

    from omuserver.server import Server


class SessionConnection(abc.ABC):
    @abc.abstractmethod
    async def send(self, packet: Packet, packet_mapper: PacketMapper) -> None: ...

    @abc.abstractmethod
    async def receive(self, packet_mapper: PacketMapper) -> Packet | None: ...

    @abc.abstractmethod
    async def close(self) -> None: ...

    @property
    @abc.abstractmethod
    def closed(self) -> bool: ...


class SessionListeners:
    def __init__(self) -> None:
        self.packet = EventEmitter[Session, Packet]()
        self.disconnected = EventEmitter[Session]()


@dataclass(frozen=True)
class Session:
    packet_mapper: PacketMapper
    app: App
    token: str
    is_dashboard: bool
    connection: SessionConnection
    _listeners: SessionListeners = field(default_factory=SessionListeners)

    @classmethod
    async def from_connection(
        cls,
        server: Server,
        packet_mapper: PacketMapper,
        connection: SessionConnection,
    ) -> Session:
        packet = await connection.receive(packet_mapper)
        if packet is None:
            raise RuntimeError("Socket closed before connect")
        if packet.type != PACKET_TYPES.CONNECT:
            raise RuntimeError(
                f"Expected {PACKET_TYPES.CONNECT.identifier} but got {packet.type}"
            )
        if not isinstance(packet.data, ConnectPacket):
            raise RuntimeError(f"Invalid packet data: {packet.data}")
        event = packet.data
        app = event.app
        token = event.token

        is_dashboard = False
        if server.config.dashboard_token and server.config.dashboard_token == token:
            is_dashboard = True
        else:
            token = await server.security.verify_app_token(app, token)
        if token is None:
            raise RuntimeError("Token is None")
        session = Session(packet_mapper, event.app, token, is_dashboard, connection)
        await session.send(PACKET_TYPES.TOKEN, token)
        return session

    @property
    def closed(self) -> bool:
        return self.connection.closed

    async def disconnect(self) -> None:
        await self.connection.close()
        await self._listeners.disconnected.emit(self)

    async def listen(self) -> None:
        try:
            while not self.connection.closed:
                packet = await self.connection.receive(self.packet_mapper)
                if packet is None:
                    break
                asyncio.create_task(self._dispatch_packet(packet))
        finally:
            await self.disconnect()

    async def _dispatch_packet(self, packet: Packet) -> None:
        await self._listeners.packet.emit(self, packet)

    async def send[T](self, packet_type: PacketType[T], data: T) -> None:
        await self.connection.send(Packet(packet_type, data), self.packet_mapper)

    @property
    def listeners(self) -> SessionListeners:
        return self._listeners

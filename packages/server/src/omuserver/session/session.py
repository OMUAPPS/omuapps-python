from __future__ import annotations

import abc
import asyncio
from typing import TYPE_CHECKING, Awaitable, List

from omu.event_emitter import EventEmitter
from omu.network.packet import PACKET_TYPES, Packet, PacketType
from omu.network.packet.packet_types import (
    ConnectPacket,
    DisconnectPacket,
    DisconnectType,
)

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
        self.ready = EventEmitter[Session]()


class SessionTask:
    def __init__(self, future: Awaitable[None], name: str) -> None:
        self.future = future
        self.name = name

    def __repr__(self) -> str:
        return f"SessionTask({self.name})"


class Session:
    def __init__(
        self,
        packet_mapper: PacketMapper,
        app: App,
        token: str,
        is_dashboard: bool,
        connection: SessionConnection,
    ) -> None:
        self.packet_mapper = packet_mapper
        self.app = app
        self.token = token
        self.is_dashboard = is_dashboard
        self.connection = connection
        self.listeners = SessionListeners()
        self.tasks: List[SessionTask] = []
        self.ready = False

    @classmethod
    async def from_connection(
        cls,
        server: Server,
        packet_mapper: PacketMapper,
        connection: SessionConnection,
    ) -> Session:
        packet = await connection.receive(packet_mapper)
        if packet is None:
            await connection.close()
            raise RuntimeError("Connection closed")
        if packet.type != PACKET_TYPES.CONNECT:
            await connection.send(
                Packet(
                    PACKET_TYPES.DISCONNECT,
                    DisconnectPacket(
                        DisconnectType.INVALID_PACKET_TYPE, "Expected connect"
                    ),
                ),
                packet_mapper,
            )
            await connection.close()
            raise RuntimeError(
                f"Expected {PACKET_TYPES.CONNECT.identifier} but got {packet.type}"
            )
        if not isinstance(packet.data, ConnectPacket):
            await connection.send(
                Packet(
                    PACKET_TYPES.DISCONNECT,
                    DisconnectPacket(
                        DisconnectType.INVALID_PACKET_TYPE, "Expected connect"
                    ),
                ),
                packet_mapper,
            )
            await connection.close()
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
            await connection.send(
                Packet(
                    PACKET_TYPES.DISCONNECT,
                    DisconnectPacket(DisconnectType.INVALID_TOKEN, "Invalid token"),
                ),
                packet_mapper,
            )
            await connection.close()
            raise RuntimeError("Invalid token")
        session = Session(packet_mapper, event.app, token, is_dashboard, connection)
        await session.send(PACKET_TYPES.TOKEN, token)
        return session

    @property
    def closed(self) -> bool:
        return self.connection.closed

    async def disconnect(
        self, disconnect_type: DisconnectType, message: str | None = None
    ) -> None:
        if not self.connection.closed:
            await self.send(
                PACKET_TYPES.DISCONNECT, DisconnectPacket(disconnect_type, message)
            )
        await self.connection.close()
        await self.listeners.disconnected.emit(self)

    async def listen(self) -> None:
        while not self.connection.closed:
            packet = await self.connection.receive(self.packet_mapper)
            if packet is None:
                await self.disconnect(DisconnectType.CLOSE)
                return
            await self.dispatch_packet(packet)

    async def dispatch_packet(self, packet: Packet) -> None:
        coro = self.listeners.packet.emit(self, packet)
        asyncio.create_task(coro)

    async def send[T](self, packet_type: PacketType[T], data: T) -> None:
        await self.connection.send(Packet(packet_type, data), self.packet_mapper)

    def add_task(self, task: SessionTask) -> None:
        if self.ready:
            raise RuntimeError("Session is already ready")
        self.tasks.append(task)

    async def wait_for_tasks(self) -> None:
        if self.ready:
            raise RuntimeError("Session is already ready")
        await asyncio.gather(*[task.future for task in self.tasks])
        self.tasks.clear()
        self.ready = True
        await self.listeners.ready.emit(self)

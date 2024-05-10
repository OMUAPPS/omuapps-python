from __future__ import annotations

import abc
import asyncio
from dataclasses import dataclass

from loguru import logger
from omu import App
from omu.errors import DisconnectReason
from omu.event_emitter import EventEmitter
from omu.network.packet import PACKET_TYPES, Packet, PacketType
from omu.network.packet.packet_types import (
    ConnectPacket,
    DisconnectPacket,
    DisconnectType,
)
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


class SessionEvents:
    def __init__(self) -> None:
        self.packet = EventEmitter[Session, Packet]()
        self.disconnected = EventEmitter[Session]()
        self.ready = EventEmitter[Session]()


@dataclass
class SessionTask:
    session: Session
    start_future: asyncio.Future[None]
    future: asyncio.Future[None]
    name: str

    def set(self) -> None:
        self.future.set_result(None)

    def __repr__(self) -> str:
        return f"SessionTask({self.name})"


class Session:
    def __init__(
        self,
        packet_mapper: PacketMapper,
        app: App,
        token: str,
        is_dashboard: bool,
        is_plugin: bool,
        connection: SessionConnection,
    ) -> None:
        self.packet_mapper = packet_mapper
        self.app = app
        self.token = token
        self.is_dashboard = is_dashboard
        self.is_plugin = is_plugin
        self.connection = connection
        self.event = SessionEvents()
        self.ready_tasks: list[SessionTask] = []
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
                f"Expected {PACKET_TYPES.CONNECT.id} but got {packet.type}"
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

        if token and await server.security.is_plugin_token(token):
            session = Session(
                packet_mapper=packet_mapper,
                app=app,
                token=token,
                is_dashboard=False,
                is_plugin=True,
                connection=connection,
            )
            return session

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
        session = Session(
            packet_mapper=packet_mapper,
            app=app,
            token=token,
            is_dashboard=is_dashboard,
            is_plugin=False,
            connection=connection,
        )
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
        await self.event.disconnected.emit(self)

    async def listen(self) -> None:
        while not self.connection.closed:
            packet = await self.connection.receive(self.packet_mapper)
            if packet is None:
                await self.disconnect(DisconnectType.CLOSE)
                return
            asyncio.create_task(self.dispatch_packet(packet))

    async def dispatch_packet(self, packet: Packet) -> None:
        try:
            await self.event.packet.emit(self, packet)
        except DisconnectReason as reason:
            logger.opt(exception=reason).error("Disconnecting session")
            await self.disconnect(reason.type, reason.message)

    async def send[T](self, packet_type: PacketType[T], data: T) -> None:
        await self.connection.send(Packet(packet_type, data), self.packet_mapper)

    async def create_ready_task(self, name: str) -> SessionTask:
        if self.ready:
            raise RuntimeError("Session is already ready")
        start_future = asyncio.Future()
        future = asyncio.Future()
        task = SessionTask(
            session=self,
            start_future=start_future,
            future=future,
            name=name,
        )
        self.ready_tasks.append(task)
        await start_future
        return task

    async def wait_for_tasks(self) -> None:
        if self.ready:
            raise RuntimeError("Session is already ready")
        for task in self.ready_tasks:
            task.start_future.set_result(None)
            await task.future
        self.ready_tasks.clear()
        self.ready = True
        await self.event.ready.emit(self)

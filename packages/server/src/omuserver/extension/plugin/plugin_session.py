from __future__ import annotations

import asyncio

from loguru import logger
from omu.network.packet import PACKET_TYPES, Packet
from omu.app import App
from omu.network.packet.packet import PacketType
from omuserver.extension.plugin.plugin_connection import PluginConnection

from omuserver.security import Permission
from omuserver.server import Server
from omuserver.session import Session
from omuserver.session.session import SessionListeners


class PluginSession(Session):
    def __init__(
        self, connection: PluginConnection, app: App, permissions: Permission
    ) -> None:
        self.connection = connection
        self._app = app
        self._permissions = permissions
        self._listeners = SessionListeners()

    @property
    def app(self) -> App:
        return self._app

    @property
    def closed(self) -> bool:
        return self.connection.closed

    @property
    def permissions(self) -> Permission:
        return self.permissions

    @classmethod
    async def create(
        cls, server: Server, connection: PluginConnection
    ) -> PluginSession:
        packet = await connection.dequeue_to_server_packet()
        if packet is None:
            raise RuntimeError("Socket closed before connect")
        if packet.packet_type != PACKET_TYPES.Connect:
            raise RuntimeError(
                f"Expected {PACKET_TYPES.Connect.type} but got {packet.packet_type}"
            )

        permissions, token = await server.security.authenticate_app(
            packet.packet_data.app, packet.packet_data.token
        )
        session = cls(connection, app=packet.packet_data.app, permissions=permissions)
        await session.send(PACKET_TYPES.Token, token)
        return session

    async def listen(self) -> None:
        try:
            while True:
                packet = await self.connection.dequeue_to_server_packet()
                if packet is None:
                    break
                asyncio.create_task(self._listeners.packet.emit(self, packet))
        finally:
            await self.disconnect()

    async def disconnect(self) -> None:
        try:
            await self.connection.close()
        except Exception as e:
            logger.warning(f"Error closing socket: {e}")
            logger.error(e)
        await self._listeners.disconnected.emit(self)

    async def send[T](self, packet_type: PacketType[T], data: T) -> None:
        if self.closed:
            raise ValueError("Socket is closed")
        self.connection.add_receive(Packet(packet_type, data))

    @property
    def listeners(self) -> SessionListeners:
        return self._listeners

    def __repr__(self) -> str:
        return f"AiohttpSession({self._app})"

    def hash(self) -> int:
        return hash(self._app)

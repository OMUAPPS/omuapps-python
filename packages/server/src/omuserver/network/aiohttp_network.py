from __future__ import annotations
from dataclasses import dataclass, field

import socket
from typing import TYPE_CHECKING, Dict

from aiohttp import web
from loguru import logger
from omu import App
from omu.helper import Coro
from omu.network.packet import PACKET_TYPES
from omu.network.packet.packet import PacketType
from omu.network.packet.packet_types import ConnectPacket
from omu.event_emitter import EventEmitter
from omuserver.network.packet_dispatcher import ServerPacketDispatcher
from omuserver.session.aiohttp_session import WebsocketsConnection

from .network import Network
from .network import NetworkListeners
from omuserver.session import Session

if TYPE_CHECKING:
    from omuserver.server import Server


@dataclass
class PacketListeners[T]:
    event_type: PacketType
    listeners: EventEmitter[Session, T] = field(default_factory=EventEmitter)


class AiohttpNetwork(Network):
    def __init__(
        self, server: Server, packet_dispatcher: ServerPacketDispatcher
    ) -> None:
        self._server = server
        self._packet_dispatcher = packet_dispatcher
        self._listeners = NetworkListeners()
        self._sessions: Dict[str, Session] = {}
        self._app = web.Application()
        self.add_websocket_route("/ws")
        self.register_packet(PACKET_TYPES.Connect, PACKET_TYPES.Ready)
        self.listeners.connected += self._packet_dispatcher.process_connection

    def register_packet(self, *packet_types: PacketType) -> None:
        self._packet_dispatcher.register(*packet_types)

    def add_http_route(
        self, path: str, handle: Coro[[web.Request], web.StreamResponse]
    ) -> None:
        self._app.router.add_get(path, handle)

    def add_websocket_route(self, path: str) -> None:
        async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            connection = WebsocketsConnection(ws)
            session = await Session.from_connection(
                self._server,
                self._packet_dispatcher.packet_mapper,
                connection,
            )
            await self.process_session(session)
            return ws

        self._app.router.add_get(path, websocket_handler)

    async def process_session(self, session: Session) -> None:
        if self.is_connected(session.app):
            logger.warning(f"Session {session.app} already connected")
            await self._sessions[session.app.key()].disconnect()
            return
        self._sessions[session.app.key()] = session
        session.listeners.disconnected += self.handle_disconnection
        await self._listeners.connected.emit(session)
        await session.send(PACKET_TYPES.Connect, ConnectPacket(app=session.app))
        await session.listen()

    def is_connected(self, app: App) -> bool:
        return app.key() in self._sessions

    async def handle_disconnection(self, session: Session) -> None:
        if session.app.key() not in self._sessions:
            return
        self._sessions.pop(session.app.key())
        await self._listeners.disconnected.emit(session)

    async def _handle_start(self, app: web.Application) -> None:
        await self._listeners.start.emit()

    def is_port_available(self) -> bool:
        try:
            socket_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = socket_connection.connect_ex(("127.0.0.1", 80))
            socket_connection.close()
            return result != 0
        except OSError:
            return False

    async def start(self) -> None:
        if not self.is_port_available():
            raise OSError(f"Port {self._server.address.port} already in use")
        self._app.on_startup.append(self._handle_start)
        runner = web.AppRunner(self._app)
        await runner.setup()
        site = web.TCPSite(
            runner, host=self._server.address.host, port=self._server.address.port
        )
        await site.start()

    @property
    def listeners(self) -> NetworkListeners:
        return self._listeners

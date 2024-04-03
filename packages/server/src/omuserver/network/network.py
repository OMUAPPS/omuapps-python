from __future__ import annotations

import socket
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict

import psutil
from aiohttp import web
from loguru import logger
from omu import App, Identifier
from omu.event_emitter import EventEmitter
from omu.helper import Coro
from omu.network.packet import PACKET_TYPES, PacketType
from omu.network.packet.packet_types import ConnectPacket

from omuserver.network.packet_dispatcher import ServerPacketDispatcher
from omuserver.session import Session
from omuserver.session.aiohttp_connection import WebsocketsConnection

if TYPE_CHECKING:
    from omuserver.server import Server


@dataclass(frozen=True)
class PacketListeners[T]:
    event_type: PacketType
    listeners: EventEmitter[Session, T] = field(default_factory=EventEmitter)


class Network:
    def __init__(
        self, server: Server, packet_dispatcher: ServerPacketDispatcher
    ) -> None:
        self._server = server
        self._packet_dispatcher = packet_dispatcher
        self._listeners = NetworkListeners()
        self._sessions: Dict[str, Session] = {}
        self._app = web.Application()
        self.add_websocket_route("/ws")
        self.register_packet(PACKET_TYPES.CONNECT, PACKET_TYPES.READY)
        self.listeners.connected += self._packet_dispatcher.process_connection

    def register_packet(self, *packet_types: PacketType) -> None:
        self._packet_dispatcher.register(*packet_types)

    def add_http_route(
        self, path: str, handle: Coro[[web.Request], web.StreamResponse]
    ) -> None:
        self._app.router.add_get(path, handle)

    def _validate_origin(self, request: web.Request, session: Session) -> None:
        origin = request.headers.get("origin")
        if origin is None:
            return
        origin_namespace = Identifier.namespace_from_url(origin)
        namespace = session.app.identifier.namespace
        if origin_namespace == namespace:
            return

        if self._server.config.strict_origin:
            raise ValueError(f"Invalid origin: {origin_namespace} != {namespace}")
        else:
            logger.warning(f"Invalid origin: {origin_namespace} != {namespace}")

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
            self._validate_origin(request, session)
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
        await session.send(PACKET_TYPES.CONNECT, ConnectPacket(app=session.app))
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
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(
                    (
                        self._server.address.host or "127.0.0.1",
                        self._server.address.port,
                    )
                )
                return True
        except OSError:
            return False

    def get_process_by_port(self, port: int) -> psutil.Process | None:
        for connection in psutil.net_connections():
            if connection.laddr and connection.laddr.port == port:
                return psutil.Process(connection.pid)
        return None

    async def start(self) -> None:
        if not self.is_port_available():
            process = self.get_process_by_port(self._server.address.port)
            if process is None:
                raise OSError(f"Port {self._server.address.port} already in use")
            port = self._server.address.port
            name = process.name()
            pid = process.pid
            raise OSError(f"Port {port} already in use by {name} ({pid=})")
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


class NetworkListeners:
    def __init__(self) -> None:
        self.start = EventEmitter()
        self.connected = EventEmitter[Session]()
        self.disconnected = EventEmitter[Session]()

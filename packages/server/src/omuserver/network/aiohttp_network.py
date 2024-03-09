from __future__ import annotations

import socket
from typing import TYPE_CHECKING, Dict

from aiohttp import web
from loguru import logger
from omu import App
from omu.helper import Coro
from omu.network.packet import PACKET_TYPES

from omuserver.session.aiohttp_session import AiohttpSession

from .network import Network
from .network import NetworkListeners

if TYPE_CHECKING:
    from omuserver.server import Server
    from omuserver.session import Session


class AiohttpNetwork(Network):
    def __init__(self, server: Server) -> None:
        self._server = server
        self._listeners = NetworkListeners()
        self._sessions: Dict[str, Session] = {}
        self._app = web.Application()

    def add_http_route(
        self, path: str, handle: Coro[[web.Request], web.StreamResponse]
    ) -> None:
        self._app.router.add_get(path, handle)

    def add_websocket_route(self, path: str) -> None:
        async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            session = await AiohttpSession.create(self._server, ws)
            await self._handle_session(session)
            return ws

        self._app.router.add_get(path, websocket_handler)

    async def _handle_session(self, session: Session) -> None:
        if self.is_connected(session.app):
            logger.warning(f"Session {session.app} already connected")
            await self._sessions[session.app.key()].disconnect()
            return
        self._sessions[session.app.key()] = session
        session.listeners.disconnected += self.handle_disconnection
        await self._listeners.connected.emit(session)
        await session.send(PACKET_TYPES.Ready, None)
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

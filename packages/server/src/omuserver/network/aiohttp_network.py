from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

from aiohttp import web
from loguru import logger
from omuserver.server import ServerListener
from omuserver.session import SessionListener
from omuserver.session.aiohttp_session import AiohttpSession

from omu import App
from omu.event import EVENTS

from .network import Coro, Network

if TYPE_CHECKING:
    from omuserver.server import Server
    from omuserver.session import Session

    from .network import NetworkListener


class AiohttpNetwork(Network, ServerListener, SessionListener):
    def __init__(self, server: Server) -> None:
        self._server = server
        self._listeners: List[NetworkListener] = []
        self._sessions: Dict[str, Session] = {}
        self._app = web.Application()
        server.add_listener(self)

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
        session.add_listener(self)
        for listener in self._listeners:
            await listener.on_connected(session)
        await session.send(EVENTS.Ready, None)
        await session.listen()

    def is_connected(self, app: App) -> bool:
        return app.key() in self._sessions

    async def on_disconnected(self, session: Session) -> None:
        if session.app.key() not in self._sessions:
            return
        self._sessions.pop(session.app.key())
        for listener in self._listeners:
            await listener.on_disconnected(session)

    async def _handle_start(self, app: web.Application) -> None:
        for listener in self._listeners:
            await listener.on_start()

    async def start(self) -> None:
        self._app.on_startup.append(self._handle_start)
        runner = web.AppRunner(self._app)
        await runner.setup()
        site = web.TCPSite(runner, self._server.address.host, self._server.address.port)
        await site.start()

    def add_listener(self, listener: NetworkListener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: NetworkListener) -> None:
        self._listeners.remove(listener)

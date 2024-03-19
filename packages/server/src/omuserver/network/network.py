from __future__ import annotations

import socket
import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict

import aiohttp
import uvicorn
from aiohttp import ClientSession
from fastapi import FastAPI, WebSocket, responses
from loguru import logger
from omu import App, Identifier
from omu.event_emitter import EventEmitter
from omu.network.packet import PACKET_TYPES, PacketType
from omu.network.packet.packet_types import ConnectPacket

from omuserver.helper import safe_path_join
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
        self.register_packet(PACKET_TYPES.CONNECT, PACKET_TYPES.READY)
        self.listeners.connected += self._packet_dispatcher.process_connection
        self.api = FastAPI(on_startup=[self._handle_start])
        self.api.add_websocket_route("/ws", self.websocket_handler)
        self.api.add_api_route("/proxy", self._handle_proxy)
        self.api.add_api_route("/asset", self._handle_assets)
        self.client = ClientSession(
            headers={
                "User-Agent": "omuserver",
            }
        )

    def register_packet(self, *packet_types: PacketType) -> None:
        self._packet_dispatcher.register(*packet_types)

    async def _handle_proxy(self, url: str, no_cache: bool = False):
        if not url:
            return responses.JSONResponse(status_code=400, content={"error": "No URL"})
        try:
            async with self.client.get(url) as resp:
                headers = {
                    "Cache-Control": "no-cache" if no_cache else "max-age=3600",
                    "Content-Type": resp.content_type,
                }
                resp.raise_for_status()
                return responses.Response(
                    status_code=resp.status,
                    content=await resp.read(),
                    headers=headers,
                )
        except aiohttp.ClientResponseError as e:
            return responses.JSONResponse(
                status_code=e.status, content={"error": str(e)}
            )
        except Exception as e:
            logger.error(e)
            return responses.JSONResponse(status_code=500, content={"error": str(e)})

    async def _handle_assets(self, id: str):
        if not id:
            return responses.JSONResponse(status_code=400, content={"error": "No ID"})
        identifier = Identifier.from_key(id)
        path = identifier.to_path()
        try:
            path = safe_path_join(self._server.directories.assets, path)

            if not path.exists():
                return responses.JSONResponse(
                    status_code=404, content={"error": "Asset not found"}
                )
            return responses.FileResponse(path)
        except Exception as e:
            logger.error(e)
            return responses.JSONResponse(status_code=500, content={"error": str(e)})

    async def websocket_handler(self, ws: WebSocket) -> None:
        await ws.accept()
        connection = WebsocketsConnection(ws)
        session = await Session.from_connection(
            self._server,
            self._packet_dispatcher.packet_mapper,
            connection,
        )
        await self.process_session(session)

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

    async def _handle_start(self) -> None:
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

        # config = uvicorn.Config(
        #     self.api,
        #     host=self._server.address.host,
        #     port=self._server.address.port,
        # )
        # server = uvicorn.Server(config)
        # await server.serve()
        def run():
            uvicorn.run(
                self.api,
                host=self._server.address.host,
                port=self._server.address.port,
            )

        thread = threading.Thread(target=run)
        thread.start()

    @property
    def listeners(self) -> NetworkListeners:
        return self._listeners


class NetworkListeners:
    def __init__(self) -> None:
        self.start = EventEmitter()
        self.connected = EventEmitter[Session]()
        self.disconnected = EventEmitter[Session]()

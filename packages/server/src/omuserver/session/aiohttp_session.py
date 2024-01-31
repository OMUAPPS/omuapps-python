from __future__ import annotations

import json
import struct
from typing import Any, List

from aiohttp import web
from loguru import logger
from omu.event import EVENTS, EventJson, EventType
from omu.extension.server.model.app import App

from omuserver.security import Permission
from omuserver.server import Server
from omuserver.session import Session, SessionListener


class AiohttpSession(Session):
    def __init__(
        self, socket: web.WebSocketResponse, app: App, permissions: Permission
    ) -> None:
        self.socket = socket
        self._app = app
        self._permissions = permissions
        self._listeners: List[SessionListener] = []

    @property
    def app(self) -> App:
        return self._app

    @property
    def closed(self) -> bool:
        return self.socket.closed

    @property
    def permissions(self) -> Permission:
        return self.permissions

    @classmethod
    async def _receive(cls, socket: web.WebSocketResponse) -> EventJson[Any]:
        msg = await socket.receive()
        match msg.type:
            case web.WSMsgType.CLOSE:
                raise RuntimeError("Socket closed")
            case web.WSMsgType.ERROR:
                raise RuntimeError("Socket error")
            case web.WSMsgType.CLOSED:
                raise RuntimeError("Socket closed")
            case web.WSMsgType.CLOSING:
                raise RuntimeError("Socket closing")
        if msg.data is None:
            raise RuntimeError("Received empty message")
        if msg.type == web.WSMsgType.TEXT:
            return EventJson.from_json(msg.json())
        elif msg.type == web.WSMsgType.BINARY:
            type_length = struct.unpack("B", msg.data[:1])[0]
            type_buff = msg.data[1 : type_length + 1]
            data_buff = msg.data[type_length + 1 :]
            type = type_buff.decode("utf-8")
            data = json.loads(data_buff.decode("utf-8"))
            return EventJson(type, data)
        else:
            raise RuntimeError(f"Unknown message type {msg.type}")

    @classmethod
    async def create(
        cls, server: Server, socket: web.WebSocketResponse
    ) -> AiohttpSession:
        data = await cls._receive(socket)
        if data.type != EVENTS.Connect.type:
            raise RuntimeError(f"Expected {EVENTS.Connect.type} but got {data.type}")
        event = EVENTS.Connect.serializer.deserialize(data.data)
        permissions, token = await server.security.auth_app(event.app, event.token)
        self = cls(socket, app=event.app, permissions=permissions)
        await self.send(EVENTS.Token, token)
        return self

    async def listen(self) -> None:
        try:
            while True:
                try:
                    event = await self._receive(self.socket)
                    for listener in self._listeners:
                        await listener.on_event(self, event)
                except RuntimeError:
                    break
        finally:
            await self.disconnect()

    async def disconnect(self) -> None:
        try:
            await self.socket.close()
        except Exception as e:
            logger.warning(f"Error closing socket: {e}")
            logger.error(e)
        for listener in self._listeners:
            await listener.on_disconnected(self)

    async def send[T](self, type: EventType[Any, T], data: T) -> None:
        if self.closed:
            raise ValueError("Socket is closed")
        type_buff = type.type.encode("utf-8")
        data_buff = json.dumps(type.serializer.serialize(data)).encode("utf-8")
        type_length = struct.pack("B", len(type_buff))
        await self.socket.send_bytes(type_length + type_buff + data_buff)

    def add_listener(self, listener: SessionListener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: SessionListener) -> None:
        self._listeners.remove(listener)

    def __str__(self) -> str:
        return f"AiohttpSession({self._app})"

    def __repr__(self) -> str:
        return str(self)

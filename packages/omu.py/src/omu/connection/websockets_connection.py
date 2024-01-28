import asyncio
from typing import Any, List

import aiohttp
from aiohttp import web
from loguru import logger

from omu.client import Client
from omu.connection import Address, Connection, ConnectionListener
from omu.event import EVENTS, EventJson
from omu.event.event import EventType
from omu.event.events import ConnectEvent


class WebsocketsConnection(Connection):
    def __init__(self, client: Client, address: Address):
        self._client = client
        self._address = address
        self._connected = False
        self._listeners: List[ConnectionListener] = []
        self._socket: aiohttp.ClientWebSocketResponse | None = None
        self._session = aiohttp.ClientSession()
        self._token: str | None = None
        self._closed_event = asyncio.Event()

    @property
    def address(self) -> Address:
        return self._address

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def _ws_endpoint(self) -> str:
        protocol = "wss" if self._address.secure else "ws"
        return f"{protocol}://{self._address.host}:{self._address.port}/ws"

    async def connect(
        self, *, token: str | None = None, reconnect: bool = True
    ) -> None:
        if self._socket and not self._socket.closed:
            raise RuntimeError("Already connected")
        self._token = token

        while True:
            await self.disconnect()
            await self._connect()
            await self.send(
                EVENTS.Connect,
                ConnectEvent(
                    app=self._client.app,
                    token=self._token,
                ),
            )
            self._closed_event.clear()
            self._client.loop.create_task(self._listen())
            for listener in self._listeners:
                await listener.on_connected()
                await listener.on_status_changed("connected")
            await self._closed_event.wait()
            if not reconnect:
                break

    async def _connect(self):
        self._socket = await self._session.ws_connect(self._ws_endpoint)
        self._connected = True

    async def _listen(self) -> None:
        try:
            while True:
                if not self._socket:
                    break
                msg = await self._socket.receive()
                if msg.type == web.WSMsgType.CLOSE:
                    break
                elif msg.type == web.WSMsgType.ERROR:
                    break
                elif msg.type == web.WSMsgType.CLOSED:
                    break
                if msg.data is None:
                    continue
                try:
                    event = EventJson.from_json(msg.json())
                except TypeError as e:
                    logger.error(f"Failed to parse event: {e} {msg}")
                    raise e
                self._client.loop.create_task(self._dispatch(event))
        finally:
            await self.disconnect()

    async def _dispatch(self, event: EventJson) -> None:
        if event.type == EVENTS.Token.type:
            self._token = event.data
        for listener in self._listeners:
            await listener.on_event(event)

    async def disconnect(self) -> None:
        if not self._socket:
            return
        if not self._socket.closed:
            try:
                await self._socket.close()
            except AttributeError:
                pass
        self._socket = None
        self._connected = False
        self._closed_event.set()
        for listener in self._listeners:
            await listener.on_disconnected()
            await listener.on_status_changed("disconnected")

    async def send[T](self, event: EventType[T, Any], data: T) -> None:
        if not self._socket or self._socket.closed or not self._connected:
            raise RuntimeError("Not connected")
        await self._socket.send_json(
            {
                "type": event.type,
                "data": event.serializer.serialize(data),
            }
        )

    def add_listener[T: ConnectionListener](self, listener: T) -> T:
        self._listeners.append(listener)
        return listener

    def remove_listener[T: ConnectionListener](self, listener: T) -> T:
        self._listeners.remove(listener)
        return listener

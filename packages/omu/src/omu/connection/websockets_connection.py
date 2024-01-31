import asyncio
import struct
from typing import List

import aiohttp
from aiohttp import web

from omu.client import Client
from omu.connection import Address, Connection, ConnectionListener
from omu.event import EVENTS, EventData
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

    async def _receive(self, socket: aiohttp.ClientWebSocketResponse) -> EventData:
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
            # return EventJson.from_json(msg.json())
            raise RuntimeError("Received text message")
        elif msg.type == web.WSMsgType.BINARY:
            type_length = struct.unpack("B", msg.data[:1])[0]
            type_buff = msg.data[1 : type_length + 1]
            type = type_buff.decode("utf-8")
            data = msg.data[type_length + 1 :]
            return EventData(type, data)
        else:
            raise RuntimeError(f"Unknown message type {msg.type}")

    async def _listen(self) -> None:
        try:
            while self._socket:
                event = await self._receive(self._socket)
                self._client.loop.create_task(self._dispatch(event))
        finally:
            await self.disconnect()

    async def _dispatch(self, event: EventData) -> None:
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

    async def send[T](self, event: EventType[T], data: T) -> None:
        if not self._socket or self._socket.closed or not self._connected:
            raise RuntimeError("Not connected")
        type_buff = event.type.encode("utf-8")
        data_buff = event.serializer.serialize(data)
        type_length = struct.pack("B", len(type_buff))
        await self._socket.send_bytes(type_length + type_buff + data_buff)

    def add_listener[T: ConnectionListener](self, listener: T) -> T:
        self._listeners.append(listener)
        return listener

    def remove_listener[T: ConnectionListener](self, listener: T) -> T:
        self._listeners.remove(listener)
        return listener

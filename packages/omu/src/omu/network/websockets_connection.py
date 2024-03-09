from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Callable, Coroutine, List

import aiohttp
from aiohttp import web

from omu.network import Address, Connection, ConnectionListeners
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.network.packet.packet import PacketData, PacketType
from omu.network.packet.packet_types import PACKET_TYPES, ConnectPacket

if TYPE_CHECKING:
    from omu.client import Client


class WebsocketsConnection(Connection):
    def __init__(self, client: Client, address: Address):
        self._client = client
        self._address = address
        self._connected = False
        self._listeners = ConnectionListeners()
        self._socket: aiohttp.ClientWebSocketResponse | None = None
        self._tasks: List[Callable[[], Coroutine[None, None, None]]] = []
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
        await self.disconnect()
        await self._connect()
        await self.send(
            PACKET_TYPES.Connect,
            ConnectPacket(
                app=self._client.app,
                token=self._token,
            ),
        )
        self._closed_event.clear()
        self._client.loop.create_task(self._listen())

        await self._listeners.connected.emit()
        await self._listeners.status_changed.emit("connected")
        for task in self._tasks:
            self._client.loop.create_task(task())

        await self._closed_event.wait()

        if reconnect:
            await self.connect()

    async def _connect(self):
        self._socket = await self._session.ws_connect(self._ws_endpoint)
        self._connected = True

    async def _receive(self, socket: aiohttp.ClientWebSocketResponse) -> PacketData:
        msg = await socket.receive()
        if msg.type in {
            web.WSMsgType.CLOSE,
            web.WSMsgType.CLOSED,
            web.WSMsgType.CLOSING,
            web.WSMsgType.ERROR,
        }:
            raise RuntimeError(f"Socket {msg.type.name.lower()}")
        if msg.data is None:
            raise RuntimeError("Received empty message")
        if msg.type == web.WSMsgType.TEXT:
            raise RuntimeError("Received text message")
        elif msg.type == web.WSMsgType.BINARY:
            with ByteReader(msg.data) as reader:
                event_type = reader.read_string()
                event_data = reader.read_byte_array()
            return PacketData(event_type, event_data)
        else:
            raise RuntimeError(f"Unknown message type {msg.type}")

    async def _listen(self) -> None:
        try:
            while self._socket:
                event = await self._receive(self._socket)
                task = self._listeners.packet.emit(event)
                self._client.loop.create_task(task)
        finally:
            await self.disconnect()

    async def disconnect(self) -> None:
        if not self._socket or self._socket.closed:
            return
        if self._socket:
            try:
                await self._socket.close()
            except AttributeError:
                pass
        self._socket = None
        self._connected = False
        self._closed_event.set()
        await self._listeners.disconnected.emit()
        await self._listeners.status_changed.emit("disconnected")

    async def send[T](self, event: PacketType[T], data: T) -> None:
        if not self._socket or self._socket.closed or not self._connected:
            raise RuntimeError("Not connected")
        writer = ByteWriter()
        writer.write_string(event.type)
        writer.write_byte_array(event.serializer.serialize(data))
        await self._socket.send_bytes(writer.finish())

    @property
    def listeners(self) -> ConnectionListeners:
        return self._listeners

    def add_task(self, task: Callable[[], Coroutine[None, None, None]]) -> None:
        self._tasks.append(task)

    def remove_task(self, task: Callable[[], Coroutine[None, None, None]]) -> None:
        self._tasks.remove(task)

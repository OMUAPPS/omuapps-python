from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Literal

from omu.client.client import Client
from omu.event_emitter import EventEmitter
from omu.helper import Coro
from omu.network.connection import Connection, PacketMapper
from omu.network.packet.packet import Packet, PacketType
from omu.network.packet.packet_types import PACKET_TYPES, ConnectPacket


@dataclass
class PacketListeners[T]:
    event_type: PacketType[T]
    listeners: EventEmitter[T] = field(default_factory=EventEmitter)


class Network:
    def __init__(self, client: Client, connection: Connection):
        self._client = client
        self._connection = connection
        self._connected = False
        self._listeners = NetworkListeners()
        self._tasks: List[Coro[[], None]] = []
        self._token: str | None = None
        self._closed_event = asyncio.Event()
        self._packet_mapper = PacketMapper()
        self._packet_handlers: Dict[str, PacketListeners] = {}
        self._packet_mapper.register(
            PACKET_TYPES.Connect,
            PACKET_TYPES.Disconnect,
            PACKET_TYPES.Token,
            PACKET_TYPES.Ready,
        )

    def set_connection(self, connection: Connection) -> None:
        if self._connected:
            raise RuntimeError("Already connected")
        if self._connection:
            del self._connection
        self._connection = connection

    def register_packet(self, *packet_types: PacketType) -> None:
        self._packet_mapper.register(*packet_types)
        for packet_type in packet_types:
            if self._packet_handlers.get(packet_type.type):
                raise ValueError(f"Event type {packet_type.type} already registered")
            self._packet_handlers[packet_type.type] = PacketListeners(packet_type)

    def add_packet_handler[T](
        self,
        packet_type: PacketType[T],
        packet_handler: Coro[[T], None] | None = None,
    ):
        if not self._packet_handlers.get(packet_type.type):
            raise ValueError(f"Event type {packet_type.type} not registered")

        def decorator(packet_handler: Coro[[T], None]) -> None:
            self._packet_handlers[packet_type.type].listeners += packet_handler

        if packet_handler:
            decorator(packet_handler)
        return decorator

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(
        self, *, token: str | None = None, reconnect: bool = True
    ) -> None:
        if self._connected:
            raise RuntimeError("Already connected")

        self._token = token
        await self.disconnect()
        await self._connection.connect()
        self._connected = True
        await self.send(
            Packet(
                PACKET_TYPES.Connect,
                ConnectPacket(
                    app=self._client.app,
                    token=self._token,
                ),
            )
        )
        self._closed_event.clear()
        self._client.loop.create_task(self._listen())

        await self._listeners.status_changed.emit("connected")
        await self._listeners.connected.emit()
        self._client.loop.create_task(self._dispatch_tasks())

        await self._closed_event.wait()

        if reconnect:
            await self.connect()

    async def _listen(self) -> None:
        try:
            while not self._connection.closed:
                packet = await self._connection.receive(self._packet_mapper)
                self._client.loop.create_task(self.dispatch_packet(packet))
        finally:
            await self.disconnect()

    async def dispatch_packet(self, packet: Packet) -> None:
        await self._listeners.packet.emit(packet)
        packet_handler = self._packet_handlers.get(packet.packet_type.type)
        if not packet_handler:
            return
        await packet_handler.listeners.emit(packet.packet_data)

    async def disconnect(self) -> None:
        if self._connection.closed:
            return
        await self._connection.close()
        self._connected = False
        self._closed_event.set()
        await self._listeners.status_changed.emit("disconnected")
        await self._listeners.disconnected.emit()

    async def send[T](self, packet: Packet[T]) -> None:
        if not self._connected:
            raise RuntimeError("Not connected")
        await self._connection.send(packet, self._packet_mapper)

    @property
    def listeners(self) -> NetworkListeners:
        return self._listeners

    def add_task(self, task: Coro[[], None]) -> None:
        self._tasks.append(task)

    def remove_task(self, task: Coro[[], None]) -> None:
        self._tasks.remove(task)

    async def _dispatch_tasks(self) -> None:
        for task in self._tasks:
            await task()


type NetworkStatus = Literal["connecting", "connected", "disconnected"]


class NetworkListeners:
    def __init__(self) -> None:
        self.connected = EventEmitter()
        self.disconnected = EventEmitter()
        self.packet = EventEmitter[Packet]()
        self.status_changed = EventEmitter[NetworkStatus]()

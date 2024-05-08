from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Literal

from loguru import logger

from omu.address import Address
from omu.client import Client
from omu.client.token import TokenProvider
from omu.errors import (
    AnotherConnection,
    InvalidOrigin,
    InvalidPacket,
    InvalidToken,
    InvalidVersion,
    OmuError,
    PermissionDenied,
)
from omu.event_emitter import EventEmitter
from omu.helper import Coro
from omu.identifier import Identifier

from .connection import Connection
from .packet import Packet, PacketType
from .packet.packet_types import (
    PACKET_TYPES,
    ConnectPacket,
    DisconnectPacket,
    DisconnectType,
)
from .packet_mapper import PacketMapper


@dataclass(frozen=True)
class PacketListeners[T]:
    event_type: PacketType[T]
    listeners: EventEmitter[T] = field(default_factory=EventEmitter)


class Network:
    def __init__(
        self,
        client: Client,
        address: Address,
        token_provider: TokenProvider,
        connection: Connection,
    ):
        self._client = client
        self._address = address
        self._token_provider = token_provider
        self._connection = connection
        self._connected = False
        self._closed = False
        self._listeners = NetworkListeners()
        self._tasks: List[Coro[[], None]] = []
        self._packet_mapper = PacketMapper()
        self._packet_handlers: Dict[Identifier, PacketListeners] = {}
        self.register_packet(
            PACKET_TYPES.CONNECT,
            PACKET_TYPES.DISCONNECT,
            PACKET_TYPES.TOKEN,
            PACKET_TYPES.READY,
        )
        self.add_packet_handler(PACKET_TYPES.TOKEN, self.handle_token)
        self.add_packet_handler(PACKET_TYPES.DISCONNECT, self.handle_disconnect)
        self.add_packet_handler(PACKET_TYPES.READY, self.handle_ready)

    async def handle_token(self, token: str):
        self._token_provider.store(self._address, self._client.app, token)

    async def handle_disconnect(self, reason: DisconnectPacket):
        if reason.type in {
            DisconnectType.SHUTDOWN,
            DisconnectType.CLOSE,
        }:
            return

        self._closed = True
        ERROR_MAP: Dict[DisconnectType, type[OmuError]] = {
            DisconnectType.ANOTHER_CONNECTION: AnotherConnection,
            DisconnectType.PERMISSION_DENIED: PermissionDenied,
            DisconnectType.INVALID_TOKEN: InvalidToken,
            DisconnectType.INVALID_ORIGIN: InvalidOrigin,
            DisconnectType.INVALID_VERSION: InvalidVersion,
            DisconnectType.INVALID_PACKET: InvalidPacket,
            DisconnectType.INVALID_PACKET_TYPE: InvalidPacket,
            DisconnectType.INVALID_PACKET_DATA: InvalidPacket,
        }
        error = ERROR_MAP.get(reason.type)
        if error:
            raise error(reason.message)

    async def handle_ready(self, _: None):
        await self._client.listeners.ready.emit()

    @property
    def address(self) -> Address:
        return self._address

    def set_connection(self, connection: Connection) -> None:
        if self._connected:
            raise RuntimeError("Cannot change connection while connected")
        if self._connection:
            del self._connection
        self._connection = connection

    def set_token_provider(self, token_provider: TokenProvider) -> None:
        self._token_provider = token_provider

    def register_packet(self, *packet_types: PacketType) -> None:
        self._packet_mapper.register(*packet_types)
        for packet_type in packet_types:
            if self._packet_handlers.get(packet_type.identifier):
                raise ValueError(
                    f"Event type {packet_type.identifier} already registered"
                )
            self._packet_handlers[packet_type.identifier] = PacketListeners(packet_type)

    def add_packet_handler[T](
        self,
        packet_type: PacketType[T],
        packet_handler: Coro[[T], None] | None = None,
    ):
        if not self._packet_handlers.get(packet_type.identifier):
            raise ValueError(f"Event type {packet_type.identifier} not registered")

        def decorator(func: Coro[[T], None]) -> None:
            self._packet_handlers[packet_type.identifier].listeners.subscribe(func)

        if packet_handler:
            decorator(packet_handler)
        return decorator

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self, *, reconnect: bool = True) -> None:
        if self._connected:
            raise RuntimeError("Already connected")
        if self._closed:
            raise RuntimeError("Connection closed")

        await self.disconnect()
        try:
            await self._connection.connect()
        except Exception as e:
            if reconnect:
                logger.error(e)
                await self.try_reconnect()
                return
            else:
                raise e
        self._connected = True
        await self.send(
            Packet(
                PACKET_TYPES.CONNECT,
                ConnectPacket(
                    app=self._client.app,
                    token=self._token_provider.get(self._address, self._client.app),
                ),
            )
        )
        listen_task = self._client.loop.create_task(self._listen_task())

        await self._listeners.status.emit("connected")
        await self._listeners.connected.emit()
        await self._dispatch_tasks()

        await self.send(Packet(PACKET_TYPES.READY, None))
        await listen_task

        if reconnect:
            await self.try_reconnect()

    async def try_reconnect(self) -> None:
        if self._closed:
            return
        await asyncio.sleep(1)
        await self.connect(reconnect=True)

    async def disconnect(self) -> None:
        if self._connection.closed:
            return
        self._connected = False
        await self._connection.close()
        await self._listeners.status.emit("disconnected")
        await self._listeners.disconnected.emit()

    async def send(self, packet: Packet) -> None:
        if not self._connected:
            raise RuntimeError("Not connected")
        await self._connection.send(packet, self._packet_mapper)

    async def _listen_task(self):
        while not self._connection.closed:
            packet = await self._connection.receive(self._packet_mapper)
            self._client.loop.create_task(self.dispatch_packet(packet))

    async def dispatch_packet(self, packet: Packet) -> None:
        await self._listeners.packet.emit(packet)
        packet_handler = self._packet_handlers.get(packet.type.identifier)
        if not packet_handler:
            return
        await packet_handler.listeners.emit(packet.data)

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
        self.connected = EventEmitter[[]]()
        self.disconnected = EventEmitter[[]]()
        self.packet = EventEmitter[Packet]()
        self.status = EventEmitter[NetworkStatus]()

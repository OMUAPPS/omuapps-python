from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, List

from loguru import logger

from omu.client import Client
from omu.extension.endpoint import (
    EndpointExtension,
    EndpointExtensionType,
)
from omu.extension.extension_registry import ExtensionRegistryImpl
from omu.extension.message import (
    MessageExtension,
    MessageExtensionType,
)
from omu.extension.registry.registry_extension import (
    RegistryExtension,
    RegistryExtensionType,
)
from omu.extension.server import ServerExtension, ServerExtensionType
from omu.extension.table import TableExtension, TableExtensionType
from omu.network import Address, WebsocketsConnection
from omu.network.packet import PACKET_TYPES, PacketDispatcherImpl

if TYPE_CHECKING:
    from omu.app import App
    from omu.client import ClientListener
    from omu.extension import ExtensionRegistry
    from omu.network import Connection
    from omu.network.packet import PacketDispatcher, PacketType


class OmuClient(Client):
    def __init__(
        self,
        app: App,
        address: Address,
        connection: Connection | None = None,
        event_registry: PacketDispatcher | None = None,
        extension_registry: ExtensionRegistry | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ):
        self._loop = loop or asyncio.get_event_loop()
        self._running = False
        self._listeners: List[ClientListener] = []
        self._app = app
        self._connection = connection or WebsocketsConnection(self, address)
        self._events = event_registry or PacketDispatcherImpl(self)
        self._connection.listeners.connected += self.on_connected
        self._connection.listeners.disconnected += self.on_disconnected
        self._extensions = extension_registry or ExtensionRegistryImpl(self)

        self.events.register(PACKET_TYPES.Ready, PACKET_TYPES.Connect)
        self._tables = self.extensions.register(TableExtensionType)
        self._server = self.extensions.register(ServerExtensionType)
        self._endpoints = self.extensions.register(EndpointExtensionType)
        self._registry = self.extensions.register(RegistryExtensionType)
        self._message = self.extensions.register(MessageExtensionType)

        for listener in self._listeners:
            asyncio.run(listener.on_initialized())

    @property
    def app(self) -> App:
        return self._app

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    @property
    def connection(self) -> Connection:
        return self._connection

    @property
    def events(self) -> PacketDispatcher:
        return self._events

    @property
    def extensions(self) -> ExtensionRegistry:
        return self._extensions

    @property
    def endpoints(self) -> EndpointExtension:
        return self._endpoints

    @property
    def tables(self) -> TableExtension:
        return self._tables

    @property
    def registry(self) -> RegistryExtension:
        return self._registry

    @property
    def message(self) -> MessageExtension:
        return self._message

    @property
    def server(self) -> ServerExtension:
        return self._server

    @property
    def running(self) -> bool:
        return self._running

    async def on_connected(self) -> None:
        logger.info(f"Connected to {self._connection.address}")

    async def on_disconnected(self) -> None:
        if not self._running:
            return
        logger.warning(f"Disconnected from {self._connection.address}")

    async def send[T](self, event: PacketType[T], data: T) -> None:
        await self._connection.send(event, data)

    def run(self, *, token: str | None = None, reconnect: bool = True) -> None:
        try:
            self.loop.set_exception_handler(self.handle_exception)
            self.loop.create_task(self.start(token=token, reconnect=reconnect))
            self.loop.run_forever()
        finally:
            self.loop.close()
            asyncio.run(self.stop())

    def handle_exception(self, loop: asyncio.AbstractEventLoop, context: dict) -> None:
        logger.error(context["message"])
        exception = context.get("exception")
        if exception:
            raise exception

    async def start(self, *, token: str | None = None, reconnect: bool = True) -> None:
        if self._running:
            raise RuntimeError("Already running")
        self._running = True
        self.loop.create_task(
            self._connection.connect(token=token, reconnect=reconnect)
        )
        for listener in self._listeners:
            await listener.on_started()

    async def stop(self) -> None:
        if not self._running:
            raise RuntimeError("Not running")
        self._running = False
        await self._connection.disconnect()
        for listener in self._listeners:
            await listener.on_stopped()

    def add_listener(self, listener: ClientListener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: ClientListener) -> None:
        self._listeners.remove(listener)

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from omu.extension.endpoint import (
    EndpointExtension,
    EndpointExtensionType,
)
from omu.extension.extension_manager import ExtensionManager
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
from omu.network import Address, Network
from omu.network.packet import Packet, PacketType
from omu.network.websocket_connection import WebsocketsConnection

from .client import Client, ClientListeners

if TYPE_CHECKING:
    from omu.app import App
    from omu.extension import ExtensionManager


class OmuClient(Client):
    def __init__(
        self,
        app: App,
        address: Address,
        connection: WebsocketsConnection | None = None,
        extension_registry: ExtensionManager | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ):
        self._loop = loop or asyncio.get_event_loop()
        self._running = False
        self._listeners = ClientListeners()
        self._app = app
        self._network = Network(self, connection or WebsocketsConnection(self, address))
        self._extensions = extension_registry or ExtensionManager(self)

        self._endpoints = self.extensions.register(EndpointExtensionType)
        self._tables = self.extensions.register(TableExtensionType)
        self._registry = self.extensions.register(RegistryExtensionType)
        self._message = self.extensions.register(MessageExtensionType)
        self._server = self.extensions.register(ServerExtensionType)

        self._loop.create_task(self._listeners.initialized.emit())

    @property
    def app(self) -> App:
        return self._app

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    @property
    def network(self) -> Network:
        return self._network

    @property
    def extensions(self) -> ExtensionManager:
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

    async def send[T](self, event: PacketType[T], data: T) -> None:
        await self._network.send(Packet(event, data))

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
        self.loop.create_task(self._network.connect(token=token, reconnect=reconnect))
        await self._listeners.started()

    async def stop(self) -> None:
        if not self._running:
            raise RuntimeError("Not running")
        self._running = False
        await self._network.disconnect()
        await self._listeners.stopped()

    @property
    def listeners(self) -> ClientListeners:
        return self._listeners

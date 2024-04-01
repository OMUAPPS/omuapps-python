from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from omu.extension.asset import ASSET_EXTENSION_TYPE, AssetExtension
from omu.extension.dashboard import (
    DASHBOARD_EXTENSION_TYPE,
    DashboardExtension,
)
from omu.extension.endpoint import (
    ENDPOINT_EXTENSION_TYPE,
    EndpointExtension,
)
from omu.extension.extension_manager import ExtensionManager
from omu.extension.message import (
    MESSAGE_EXTENSION_TYPE,
    MessageExtension,
)
from omu.extension.permission import PERMISSION_EXTENSION_TYPE, PermissionExtension
from omu.extension.registry import (
    REGISTRY_EXTENSION_TYPE,
    RegistryExtension,
)
from omu.extension.server import SERVER_EXTENSION_TYPE, ServerExtension
from omu.extension.table import TABLE_EXTENSION_TYPE, TableExtension
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
        self._network = Network(
            self,
            address,
            connection or WebsocketsConnection(self, address),
        )
        self._network.listeners.connected += self._listeners.ready.emit
        self._extensions = extension_registry or ExtensionManager(self)

        self._endpoints = self.extensions.register(ENDPOINT_EXTENSION_TYPE)
        self._tables = self.extensions.register(TABLE_EXTENSION_TYPE)
        self._registry = self.extensions.register(REGISTRY_EXTENSION_TYPE)
        self._message = self.extensions.register(MESSAGE_EXTENSION_TYPE)
        self._assets = self.extensions.register(ASSET_EXTENSION_TYPE)
        self._server = self.extensions.register(SERVER_EXTENSION_TYPE)
        self._permissions = self.extensions.register(PERMISSION_EXTENSION_TYPE)
        self._dashboard = self.extensions.register(DASHBOARD_EXTENSION_TYPE)

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
    def assets(self) -> AssetExtension:
        return self._assets

    @property
    def server(self) -> ServerExtension:
        return self._server

    @property
    def permissions(self) -> PermissionExtension:
        return self._permissions

    @property
    def dashboard(self) -> DashboardExtension:
        return self._dashboard

    @property
    def running(self) -> bool:
        return self._running

    async def send[T](self, type: PacketType[T], data: T) -> None:
        await self._network.send(Packet(type, data))

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

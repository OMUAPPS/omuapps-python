import asyncio
import json
from typing import Optional

import aiohttp
from aiohttp import web
from loguru import logger
from omu.network import Address

from omuserver import __version__
from omuserver.directories import Directories, get_directories
from omuserver.network.packet_dispatcher import ServerPacketDispatcher
from omuserver.extension import ExtensionRegistry, ExtensionRegistryServer
from omuserver.extension.asset.asset_extension import AssetExtension
from omuserver.extension.endpoint import EndpointExtension
from omuserver.extension.message.message_extension import MessageExtension
from omuserver.extension.plugin.plugin_extension import PluginExtension
from omuserver.extension.registry.registry_extension import RegistryExtension
from omuserver.extension.server import ServerExtension
from omuserver.extension.table import TableExtension
from omuserver.helper import safe_path_join
from omuserver.network import Network
from omuserver.network.aiohttp_network import AiohttpNetwork
from omuserver.network.network import NetworkListeners
from omuserver.security.security import ServerSecurity

from .server import Server, ServerListeners

client = aiohttp.ClientSession(
    headers={
        "User-Agent": json.dumps(
            [
                "omu",
                {
                    "name": "omuserver",
                    "version": __version__,
                },
            ]
        )
    }
)


class OmuServer(Server, NetworkListeners):
    def __init__(
        self,
        address: Address,
        network: Optional[Network] = None,
        extensions: Optional[ExtensionRegistry] = None,
        directories: Optional[Directories] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        self._loop = loop or asyncio.get_event_loop()
        self._address = address
        self._listeners = ServerListeners()
        self._directories = directories or get_directories()
        self._directories.mkdir()
        self._packet_dispatcher = ServerPacketDispatcher()
        self._network = network or AiohttpNetwork(self, self._packet_dispatcher)
        self._network.listeners.start += self._handle_network_start
        self._network.add_http_route("/proxy", self._handle_proxy)
        self._network.add_http_route("/assets", self._handle_assets)
        self._extensions = extensions or ExtensionRegistryServer(self)
        self._security = ServerSecurity(self)
        self._running = False
        self._endpoint = self.extensions.register(EndpointExtension)
        self._tables = self.extensions.register(TableExtension)
        self._server = self.extensions.register(ServerExtension)
        self._registry = self.extensions.register(RegistryExtension)
        self._message = self.extensions.register(MessageExtension)
        self._plugin = self.extensions.register(PluginExtension)
        self._assets = self.extensions.register(AssetExtension)

    async def _handle_proxy(self, request: web.Request) -> web.StreamResponse:
        url = request.query.get("url")
        no_cache = bool(request.query.get("no_cache"))
        if not url:
            return web.Response(status=400)
        try:
            async with client.get(url) as resp:
                headers = {
                    "Cache-Control": "no-cache" if no_cache else "max-age=3600",
                    "Content-Type": resp.content_type,
                }
                resp.raise_for_status()
                return web.Response(
                    status=resp.status,
                    headers=headers,
                    body=await resp.read(),
                )
        except aiohttp.ClientResponseError as e:
            return web.Response(status=e.status, text=e.message)
        except Exception as e:
            logger.error(e)
            return web.Response(status=500)

    async def _handle_assets(self, request: web.Request) -> web.StreamResponse:
        path = request.query.get("path")
        if not path:
            return web.Response(status=400)
        try:
            path = safe_path_join(self._directories.assets, path)

            if not path.exists():
                return web.Response(status=404)
            return web.FileResponse(path)
        except Exception as e:
            logger.error(e)
            return web.Response(status=500)

    def run(self) -> None:
        loop = self.loop

        try:
            loop.set_exception_handler(self.handle_exception)
            loop.create_task(self.start())
            loop.run_forever()
        finally:
            loop.close()
            asyncio.run(self.shutdown())

    def handle_exception(self, loop: asyncio.AbstractEventLoop, context: dict) -> None:
        logger.error(context["message"])
        exception = context.get("exception")
        if exception:
            raise exception

    async def start(self) -> None:
        self._running = True
        await self._network.start()

    async def shutdown(self) -> None:
        self._running = False
        await self._listeners.stop()

    async def _handle_network_start(self) -> None:
        logger.info(f"Listening on {self.address}")
        await self._listeners.start()

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        return self._loop

    @property
    def address(self) -> Address:
        return self._address

    @property
    def security(self) -> ServerSecurity:
        return self._security

    @property
    def directories(self) -> Directories:
        return self._directories

    @property
    def network(self) -> Network:
        return self._network

    @property
    def packet_dispatcher(self) -> ServerPacketDispatcher:
        return self._packet_dispatcher

    @property
    def extensions(self) -> ExtensionRegistry:
        return self._extensions

    @property
    def endpoints(self) -> EndpointExtension:
        return self._endpoint

    @property
    def tables(self) -> TableExtension:
        return self._tables

    @property
    def registry(self) -> RegistryExtension:
        return self._registry

    @property
    def messages(self) -> MessageExtension:
        return self._message

    @property
    def plugins(self) -> PluginExtension:
        return self._plugin

    @property
    def assets(self) -> AssetExtension:
        return self._assets

    @property
    def running(self) -> bool:
        return self._running

    @property
    def listeners(self) -> ServerListeners:
        return self._listeners

from __future__ import annotations

import asyncio
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
)

from omu.extension.plugin.plugin_extension import (
    PLUGIN_PERMISSION,
    PLUGIN_REQUIRE_PACKET,
    PLUGIN_WAIT_ENDPOINT,
    WaitResponse,
)
from packaging.specifiers import SpecifierSet

from omuserver.session import Session

from .plugin_loader import DependencyResolver, PluginLoader

if TYPE_CHECKING:
    from omuserver.server import Server


class PluginExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        self.lock = asyncio.Lock()
        self.loader = PluginLoader(server)
        self.dependency_resolver = DependencyResolver()
        server.packet_dispatcher.register(
            PLUGIN_REQUIRE_PACKET,
        )
        server.packet_dispatcher.add_packet_handler(
            PLUGIN_REQUIRE_PACKET,
            self.handle_require_packet,
        )
        server.endpoints.bind_endpoint(
            PLUGIN_WAIT_ENDPOINT,
            self.handle_wait_endpoint,
        )
        server.permissions.register(
            PLUGIN_PERMISSION,
        )
        server.listeners.start += self.on_server_start

    async def on_server_start(self) -> None:
        await self.loader.load_plugins()

    async def handle_require_packet(
        self, session: Session, packages: Dict[str, str | None]
    ) -> None:
        changed = False
        for package, version in packages.items():
            specifier = None
            if version is not None:
                specifier = SpecifierSet(version)
            if self.dependency_resolver.add_dependencies({package: specifier}):
                changed = True

        if not changed:
            return

        async with self.lock:
            await self.dependency_resolver.resolve()
            await self.loader.load_updated_plugins()

    async def handle_wait_endpoint(
        self, session: Session, plugins: List[str]
    ) -> WaitResponse:
        async with self.lock:
            for plugin in plugins:
                if plugin not in self.loader.plugins:
                    return {"success": False}
            return {"success": True}

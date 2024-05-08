from __future__ import annotations

import asyncio

from omu.extension.plugin.plugin_extension import (
    PLUGIN_PERMISSION_TYPE,
    PLUGIN_REQUIRE_PACKET,
)
from packaging.specifiers import SpecifierSet

from omuserver.server import Server
from omuserver.session import Session

from .plugin_loader import DependencyResolver, PluginLoader


class PluginExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        self.lock = asyncio.Lock()
        server.network.listeners.start += self.on_network_start
        self.loader = PluginLoader(server)
        self.dependency_resolver = DependencyResolver()
        server.packet_dispatcher.register(
            PLUGIN_REQUIRE_PACKET,
        )
        server.packet_dispatcher.add_packet_handler(
            PLUGIN_REQUIRE_PACKET,
            self.handle_require_packet,
        )
        server.permissions.register(
            PLUGIN_PERMISSION_TYPE,
        )

    async def on_network_start(self) -> None:
        await self.loader.run_plugins()

    async def handle_require_packet(
        self, session: Session, packages: dict[str, str | None]
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

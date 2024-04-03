from __future__ import annotations

from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
)

from omu.extension.plugin.plugin import PluginType
from omu.extension.plugin.plugin_extension import (
    PLUGIN_REGISTER_PACKET,
    PLUGIN_REQUIRE_PACKET,
    PLUGIN_WAIT_ENDPOINT,
    WaitResponse,
)
from omu.identifier import Identifier

from omuserver.session.session import Session

from .plugin_loader import PluginEntry, PluginLoader

if TYPE_CHECKING:
    from omuserver.server import Server


class PluginExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        self.loader = PluginLoader(server)
        self.plugins: Dict[Path, PluginEntry] = {}
        server.packet_dispatcher.register(
            PLUGIN_REGISTER_PACKET,
            PLUGIN_REQUIRE_PACKET,
        )
        server.packet_dispatcher.add_packet_handler(
            PLUGIN_REGISTER_PACKET,
            self.handle_register_packet,
        )
        server.packet_dispatcher.add_packet_handler(
            PLUGIN_REQUIRE_PACKET,
            self.handle_require_packet,
        )
        server.endpoints.bind_endpoint(
            PLUGIN_WAIT_ENDPOINT,
            self.handle_wait_endpoint,
        )
        server.listeners.start += self.on_server_start

    async def on_server_start(self) -> None:
        await self.loader.load_plugins()

    async def handle_register_packet(
        self, session: Session, plugins: List[PluginType]
    ) -> None: ...

    async def handle_require_packet(
        self, session: Session, plugins: List[PluginType]
    ) -> None: ...

    async def handle_wait_endpoint(
        self, session: Session, plugins: List[Identifier]
    ) -> WaitResponse:
        return {"success": True}

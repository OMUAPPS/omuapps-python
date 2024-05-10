from typing import Dict

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.table import TableType
from omu.network.packet import PacketType

from .plugin import PluginPackageInfo

PLUGIN_EXTENSION_TYPE = ExtensionType(
    "plugin",
    lambda client: PluginExtension(client),
    lambda: [],
)


class PluginExtension(Extension):
    def __init__(self, client: Client):
        self.client = client
        self.plugins: Dict[str, str | None] = {}

        self.client.network.register_packet(
            PLUGIN_REQUIRE_PACKET,
        )
        self.client.network.listeners.connected += self.on_connected

    async def on_connected(self):
        await self.client.send(PLUGIN_REQUIRE_PACKET, self.plugins)

    def require(self, plugins: Dict[str, str | None]):
        self.plugins.update(plugins)


PLUGIN_REQUIRE_PACKET = PacketType[Dict[str, str | None]].create_json(
    PLUGIN_EXTENSION_TYPE,
    "require",
)
PLUGIN_ALLOWED_PACKAGE_TABLE = TableType.create_model(
    PLUGIN_EXTENSION_TYPE,
    "allowed_package",
    PluginPackageInfo,
)

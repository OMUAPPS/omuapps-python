from typing import Dict

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.permission.permission import PermissionType
from omu.network.packet.packet import PacketType

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
        self.client.permissions.require(PLUGIN_PERMISSION)


PLUGIN_PERMISSION_TYPE = PermissionType(
    PLUGIN_EXTENSION_TYPE / "request",
    metadata={
        "level": "high",
        "name": {
            "en": "Require plugin",
            "ja": "プラグインの要求",
        },
        "note": {
            "en": "Require plugin",
            "ja": "プラグインの要求",
        },
    },
)
PLUGIN_PERMISSION = PLUGIN_PERMISSION_TYPE.id
PLUGIN_REQUIRE_PACKET = PacketType[Dict[str, str | None]].create_json(
    PLUGIN_EXTENSION_TYPE,
    "require",
)

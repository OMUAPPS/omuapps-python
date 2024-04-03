from typing import Dict, List, TypedDict

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint.endpoint import EndpointType
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
        await self.client.endpoints.call(PLUGIN_WAIT_ENDPOINT, [*self.plugins.keys()])

    def require(self, plugins: Dict[str, str | None]):
        self.plugins.update(plugins)
        self.client.permissions.require(PLUGIN_PERMISSION)


PLUGIN_PERMISSION = PermissionType.create(
    PLUGIN_EXTENSION_TYPE,
    "request",
)
PLUGIN_REQUIRE_PACKET = PacketType[Dict[str, str | None]].create_json(
    PLUGIN_EXTENSION_TYPE,
    "require",
)


class WaitResponse(TypedDict):
    success: bool


PLUGIN_WAIT_ENDPOINT = EndpointType[List[str], WaitResponse].create_json(
    PLUGIN_EXTENSION_TYPE,
    "wait",
)

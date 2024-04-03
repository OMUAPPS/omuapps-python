from typing import List, TypedDict

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
        self.plugins: List[str] = []

        self.client.network.register_packet(
            PLUGIN_REQUIRE_PACKET,
        )
        self.client.network.listeners.connected += self.on_connected

    async def on_connected(self):
        await self.client.send(PLUGIN_REQUIRE_PACKET, self.plugins)
        await self.client.endpoints.call(PLUGIN_WAIT_ENDPOINT, self.plugins)

    def install(self, plugin: str):
        if plugin in self.plugins:
            raise ValueError(f"Plugin {plugin} already registered")
        self.client.permissions.require(PLUGIN_PERMISSION)
        self.plugins.append(plugin)


PLUGIN_PERMISSION = PermissionType.create(
    PLUGIN_EXTENSION_TYPE,
    "Plugin",
)
PLUGIN_REQUIRE_PACKET = PacketType[str].create_json(
    PLUGIN_EXTENSION_TYPE,
    "require",
)


class WaitResponse(TypedDict):
    success: bool


PLUGIN_WAIT_ENDPOINT = EndpointType[List[str], WaitResponse].create_json(
    PLUGIN_EXTENSION_TYPE,
    "wait",
)

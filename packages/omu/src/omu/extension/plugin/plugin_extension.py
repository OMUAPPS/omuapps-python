from typing import Dict, List, TypedDict

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint.endpoint import EndpointType
from omu.extension.permission.permission import PermissionType
from omu.identifier import Identifier
from omu.network.packet.packet import PacketType
from omu.serializer import Serializer

from .plugin import PluginType

PLUGIN_EXTENSION_TYPE = ExtensionType(
    "plugin",
    lambda client: PluginExtension(client),
    lambda: [],
)


class PluginExtension(Extension):
    def __init__(self, client: Client):
        self.client = client
        self.plugins: Dict[Identifier, PluginType] = {}

        self.client.network.register_packet(
            PLUGIN_REGISTER_PACKET,
            PLUGIN_REQUIRE_PACKET,
        )
        self.client.network.listeners.connected += self.on_connected

    async def on_connected(self):
        await self.client.send(PLUGIN_REQUIRE_PACKET, [*self.plugins.values()])
        await self.client.endpoints.call(PLUGIN_WAIT_ENDPOINT, [*self.plugins.keys()])

    def install(self, plugin: PluginType):
        if plugin.identifier in self.plugins:
            raise ValueError(f"Plugin {plugin.identifier} already registered")
        self.client.permissions.require(PLUGIN_PERMISSION)
        self.plugins[plugin.identifier] = plugin


PLUGIN_PERMISSION = PermissionType.create(
    PLUGIN_EXTENSION_TYPE,
    "Plugin",
)
PLUGIN_REGISTER_PACKET = PacketType.create_json(
    PLUGIN_EXTENSION_TYPE,
    "register",
    Serializer.model(PluginType).array(),
)
PLUGIN_REQUIRE_PACKET = PacketType.create_json(
    PLUGIN_EXTENSION_TYPE,
    "require",
    Serializer.model(PluginType).array(),
)


class WaitResponse(TypedDict):
    success: bool


PLUGIN_WAIT_ENDPOINT = EndpointType[List[Identifier], WaitResponse].create_json(
    PLUGIN_EXTENSION_TYPE,
    "wait",
    request_serializer=Serializer.model(Identifier).array(),
)

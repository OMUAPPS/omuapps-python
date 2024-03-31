from typing import Dict, List, TypedDict

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint.endpoint import EndpointType
from omu.identifier import Identifier
from omu.network.packet.packet import PacketType
from omu.serializer import Serializer

from .plugin import PluginType

PluginExtensionType = ExtensionType(
    "plugin",
    lambda client: PluginExtension(client),
    lambda: [],
)


class PluginExtension(Extension):
    def __init__(self, client: Client):
        self.client = client
        self.plugins: Dict[Identifier, PluginType] = {}

        self.client.network.register_packet(
            PluginRegisterPacket,
            PluginRequirePacket,
        )
        self.client.network.listeners.connected += self.on_connected

    async def on_connected(self):
        await self.client.send(PluginRequirePacket, [*self.plugins.values()])
        await self.client.endpoints.call(PluginWaitEndpoint, [*self.plugins.keys()])

    def register(self, plugin: PluginType):
        if plugin.identifier in self.plugins:
            raise ValueError(f"Plugin {plugin.identifier} already registered")
        self.plugins[plugin.identifier] = plugin


PluginRegisterPacket = PacketType.create_json(
    PluginExtensionType,
    "register",
    Serializer.model(PluginType).array(),
)

PluginRequirePacket = PacketType.create_json(
    PluginExtensionType,
    "require",
    Serializer.model(PluginType).array(),
)


class WaitResponse(TypedDict):
    ok: bool


PluginWaitEndpoint = EndpointType[List[Identifier], WaitResponse].create_serialized(
    PluginExtensionType,
    "wait",
    request_serializer=Serializer.model(Identifier).array().pipe(Serializer.json()),
    response_serializer=Serializer.json(),
)

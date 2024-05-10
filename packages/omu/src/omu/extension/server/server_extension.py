from typing import Set

from omu.app import App
from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
from omu.extension.registry import RegistryType
from omu.extension.table import TableType
from omu.identifier import Identifier
from omu.network.packet import PacketType
from omu.serializer import Serializer

SERVER_EXTENSION_TYPE = ExtensionType(
    "server", lambda client: ServerExtension(client), lambda: []
)

APP_TABLE_TYPE = TableType.create_model(
    SERVER_EXTENSION_TYPE,
    "apps",
    App,
)
SERVER_SHUTDOWN_PERMISSION_ID = SERVER_EXTENSION_TYPE / "shutdown"
SHUTDOWN_ENDPOINT_TYPE = EndpointType[bool, bool].create_json(
    SERVER_EXTENSION_TYPE,
    "shutdown",
    permission_id=SERVER_SHUTDOWN_PERMISSION_ID,
)
REQUIRE_APPS_PACKET_TYPE = PacketType[list[Identifier]].create_json(
    SERVER_EXTENSION_TYPE,
    "require_apps",
    serializer=Serializer.model(Identifier).to_array(),
)
VERSION_REGISTRY_TYPE = RegistryType[str | None].create_json(
    SERVER_EXTENSION_TYPE,
    "version",
    default_value=None,
)


class ServerExtension(Extension):
    def __init__(self, client: Client) -> None:
        client.network.register_packet(
            REQUIRE_APPS_PACKET_TYPE,
        )
        self.client = client
        self.apps = client.tables.get(APP_TABLE_TYPE)
        self.required_apps: Set[Identifier] = set()
        client.network.event.connected += self.on_connect

    async def on_connect(self) -> None:
        await self.client.send(REQUIRE_APPS_PACKET_TYPE, [*self.required_apps])

    async def shutdown(self, restart: bool = False) -> bool:
        return await self.client.endpoints.call(SHUTDOWN_ENDPOINT_TYPE, restart)

    def require(self, *app_ids: Identifier) -> None:
        self.required_apps.update(app_ids)

from omu.app import App
from omu.client import Client
from omu.event_emitter import Unlisten
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
from omu.extension.registry import RegistryType
from omu.extension.server.packets import ConsolePacket
from omu.extension.table import TablePermissions, TableType
from omu.helper import Coro
from omu.identifier import Identifier
from omu.network.packet import PacketType
from omu.serializer import Serializer

SERVER_EXTENSION_TYPE = ExtensionType(
    "server", lambda client: ServerExtension(client), lambda: []
)

SERVER_APPS_READ_PERMISSION_ID = SERVER_EXTENSION_TYPE / "apps" / "read"
APP_TABLE_TYPE = TableType.create_model(
    SERVER_EXTENSION_TYPE,
    "apps",
    App,
    permissions=TablePermissions(
        read=SERVER_APPS_READ_PERMISSION_ID,
    ),
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
SERVER_CONSOLE_PERMISSION_ID = SERVER_EXTENSION_TYPE / "console"
CONSOLE_GET_ENDPOINT_TYPE = EndpointType[int | None, list[str]].create_json(
    SERVER_EXTENSION_TYPE,
    "console",
    permission_id=SERVER_CONSOLE_PERMISSION_ID,
)
CONSOLE_LISTEN_PACKET_TYPE = PacketType[None].create_json(
    SERVER_EXTENSION_TYPE,
    "console_listen",
)
CONSOLE_PACKET_TYPE = PacketType[ConsolePacket].create_serialized(
    SERVER_EXTENSION_TYPE,
    "console",
    serializer=ConsolePacket,
)


class ServerExtension(Extension):
    def __init__(self, client: Client) -> None:
        client.network.register_packet(
            REQUIRE_APPS_PACKET_TYPE,
            CONSOLE_LISTEN_PACKET_TYPE,
            CONSOLE_PACKET_TYPE,
        )
        client.network.add_packet_handler(CONSOLE_PACKET_TYPE, self._on_console)
        self.client = client
        self.apps = client.tables.get(APP_TABLE_TYPE)
        self.required_apps: set[Identifier] = set()
        self.console_listeners: list[Coro[[list[str]], None]] = []
        client.network.add_task(self.on_task)

    async def on_task(self) -> None:
        if self.required_apps:
            await self.client.send(REQUIRE_APPS_PACKET_TYPE, [*self.required_apps])

    async def shutdown(self, restart: bool = False) -> bool:
        return await self.client.endpoints.call(SHUTDOWN_ENDPOINT_TYPE, restart)

    def require(self, *app_ids: Identifier) -> None:
        if self.client.running:
            raise RuntimeError("Cannot require apps after the client has started")
        self.required_apps.update(app_ids)

    async def console_get(self, line_count: int | None = None) -> list[str]:
        return await self.client.endpoints.call(CONSOLE_GET_ENDPOINT_TYPE, line_count)

    async def console_listen(self, listener: Coro[[list[str]], None]) -> Unlisten:
        if len(self.console_listeners) == 0:

            async def listen():
                await self.client.send(CONSOLE_LISTEN_PACKET_TYPE, None)

            self.client.when_ready(listen)
        self.console_listeners.append(listener)
        return lambda: self.console_listeners.remove(listener)

    async def _on_console(self, packet: ConsolePacket) -> None:
        for listener in self.console_listeners:
            await listener(packet.lines)

from omu.client import Client
from omu.extension.endpoint import JsonEndpointType
from omu.extension.extension import Extension, ExtensionType
from omu.extension.server import App
from omu.extension.table import TableExtensionType, TableType

ServerExtensionType = ExtensionType(
    "server", lambda client: ServerExtension(client), lambda: []
)

AppsTableType = TableType.model(
    ServerExtensionType,
    "apps",
    App,
)
ShutdownEndpointType = JsonEndpointType[bool, bool].of_extension(
    ServerExtensionType,
    "shutdown",
)
PrintTasksEndpointType = JsonEndpointType[None, None].of_extension(
    ServerExtensionType,
    "print_tasks",
)


class ServerExtension(Extension):
    def __init__(self, client: Client) -> None:
        self.client = client
        tables = client.extensions.get(TableExtensionType)
        self.apps = tables.get(AppsTableType)

    async def shutdown(self, restart: bool = False) -> bool:
        return await self.client.endpoints.call(ShutdownEndpointType, restart)

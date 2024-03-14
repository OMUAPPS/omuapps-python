from omu.app import App
from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
from omu.extension.table import TableExtensionType, TableType

ServerExtensionType = ExtensionType(
    "server", lambda client: ServerExtension(client), lambda: []
)

AppsTableType = TableType.create_model(
    ServerExtensionType,
    "apps",
    App,
)
ShutdownEndpointType = EndpointType[bool, bool].create_json(
    ServerExtensionType,
    "shutdown",
)
PrintTasksEndpointType = EndpointType[None, None].create_json(
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

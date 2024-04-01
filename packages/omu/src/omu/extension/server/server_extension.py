from omu.app import App
from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
from omu.extension.table import TABLE_EXTENSION_TYPE, TableType

SERVER_EXTENSION_TYPE = ExtensionType(
    "server", lambda client: ServerExtension(client), lambda: []
)

APPS_TABLE_TYPE = TableType.create_model(
    SERVER_EXTENSION_TYPE,
    "apps",
    App,
)
SHUTDOWN_ENDPOINT_TYPE = EndpointType[bool, bool].create_json(
    SERVER_EXTENSION_TYPE,
    "shutdown",
)


class ServerExtension(Extension):
    def __init__(self, client: Client) -> None:
        self.client = client
        tables = client.extensions.get(TABLE_EXTENSION_TYPE)
        self.apps = tables.get(APPS_TABLE_TYPE)

    async def shutdown(self, restart: bool = False) -> bool:
        return await self.client.endpoints.call(SHUTDOWN_ENDPOINT_TYPE, restart)

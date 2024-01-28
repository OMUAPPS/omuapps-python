import base64
from typing import Dict, List

from omu.client.client import Client
from omu.connection.connection import ConnectionListener
from omu.extension.endpoint.endpoint import JsonEndpointType
from omu.extension.extension import Extension, define_extension_type

AssetExtensionType = define_extension_type(
    "asset",
    lambda client: AssetExtension(client),
    lambda: [],
)


type b64str = str

AssetUploadEndpoint = JsonEndpointType[Dict[str, b64str], List[str]].of_extension(
    AssetExtensionType,
    "upload",
)


class AssetExtension(Extension, ConnectionListener):
    def __init__(self, client: Client) -> None:
        self.client = client
        client.connection.add_listener(self)

    async def upload(self, assets: Dict[str, bytes]) -> List[str]:
        return await self.client.endpoints.call(
            AssetUploadEndpoint, {k: self._encode(v) for k, v in assets.items()}
        )

    def _encode(self, data: bytes) -> b64str:
        return base64.b64encode(data).decode("utf-8")

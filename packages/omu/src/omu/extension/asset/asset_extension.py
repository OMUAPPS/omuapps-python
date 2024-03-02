from typing import Dict, List

from omu.client import Client
from omu.extension.endpoint import SerializeEndpointType
from omu.extension.extension import Extension, ExtensionType
from omu.network import ConnectionListener
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.serializer import Serializable, Serializer

AssetExtensionType = ExtensionType(
    "asset",
    lambda client: AssetExtension(client),
    lambda: [],
)
type Files = Dict[str, bytes]


class FilesSerializer(Serializable[Files, bytes]):
    def serialize(self, data: Files) -> bytes:
        writer = ByteWriter()
        writer.write_int(len(data))
        for key, value in data.items():
            writer.write_string(key)
            writer.write_byte_array(value)
        return writer.finish()

    def deserialize(self, data: bytes) -> Files:
        with ByteReader(data) as reader:
            length = reader.read_int()
            files = {}
            for _ in range(length):
                key = reader.read_string()
                value = reader.read_byte_array()
                files[key] = value
        return files


AssetUploadEndpoint = SerializeEndpointType[Files, List[str]].of_extension(
    AssetExtensionType,
    "upload",
    request_serializer=FilesSerializer(),
    response_serializer=Serializer.json(),
)


class AssetExtension(Extension, ConnectionListener):
    def __init__(self, client: Client) -> None:
        self.client = client
        client.connection.add_listener(self)

    async def upload(self, assets: Files) -> List[str]:
        return await self.client.endpoints.call(AssetUploadEndpoint, assets)

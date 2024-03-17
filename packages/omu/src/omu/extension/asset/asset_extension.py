from typing import Dict, List

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
from omu.helper import instance
from omu.identifier import Identifier
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.serializer import Serializable, Serializer

AssetExtensionType = ExtensionType(
    "asset",
    lambda client: AssetExtension(client),
    lambda: [],
)
type Files = Dict[Identifier, bytes]


@instance
class FILES_SERIALIZER(Serializable[Files, bytes]):
    def serialize(self, data: Files) -> bytes:
        writer = ByteWriter()
        writer.write_int(len(data))
        for identifier, value in data.items():
            writer.write_string(identifier.key())
            writer.write_byte_array(value)
        return writer.finish()

    def deserialize(self, data: bytes) -> Files:
        with ByteReader(data) as reader:
            count = reader.read_int()
            files: Files = {}
            for _ in range(count):
                identifier = Identifier.from_key(reader.read_string())
                value = reader.read_byte_array()
                files[identifier] = value
        return files


IDENTIFIERS_SERIALIZER = Serializer(Identifier.key, Identifier.from_key).array().json()


AssetUploadEndpoint = EndpointType[Files, List[Identifier]].create_serialized(
    AssetExtensionType,
    "upload",
    request_serializer=FILES_SERIALIZER,
    response_serializer=IDENTIFIERS_SERIALIZER,
)
AssetDownloadEndpoint = EndpointType[List[Identifier], Files].create_serialized(
    AssetExtensionType,
    "download",
    request_serializer=IDENTIFIERS_SERIALIZER,
    response_serializer=FILES_SERIALIZER,
)


class AssetExtension(Extension):
    def __init__(self, client: Client) -> None:
        self.client = client

    async def upload(self, assets: Files) -> List[Identifier]:
        return await self.client.endpoints.call(AssetUploadEndpoint, assets)

    async def download(self, identifiers: List[Identifier]) -> Files:
        return await self.client.endpoints.call(AssetDownloadEndpoint, identifiers)

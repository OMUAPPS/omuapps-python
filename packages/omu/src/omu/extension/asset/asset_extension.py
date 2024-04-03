from typing import List, Mapping

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
from omu.helper import instance
from omu.identifier import Identifier
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.serializer import Serializable, Serializer

ASSET_EXTENSION_TYPE = ExtensionType(
    "asset",
    lambda client: AssetExtension(client),
    lambda: [],
)
type Files = Mapping[Identifier, bytes]


@instance
class FILES_SERIALIZER(Serializable[Files, bytes]):
    def serialize(self, item: Files) -> bytes:
        writer = ByteWriter()
        writer.write_int(len(item))
        for identifier, value in item.items():
            writer.write_string(identifier.key())
            writer.write_byte_array(value)
        return writer.finish()

    def deserialize(self, item: bytes) -> Files:
        with ByteReader(item) as reader:
            count = reader.read_int()
            files: Files = {}
            for _ in range(count):
                identifier = Identifier.from_key(reader.read_string())
                value = reader.read_byte_array()
                files[identifier] = value
        return files


ASSET_UPLOAD_ENDPOINT = EndpointType[Files, List[Identifier]].create_serialized(
    ASSET_EXTENSION_TYPE,
    "upload",
    request_serializer=FILES_SERIALIZER,
    response_serializer=Serializer.model(Identifier).array().pipe(Serializer.json()),
)
ASSET_DOWNLOAD_ENDPOINT = EndpointType[List[Identifier], Files].create_serialized(
    ASSET_EXTENSION_TYPE,
    "download",
    request_serializer=Serializer.model(Identifier).array().pipe(Serializer.json()),
    response_serializer=FILES_SERIALIZER,
)


class AssetExtension(Extension):
    def __init__(self, client: Client) -> None:
        self.client = client

    async def upload(self, assets: Files) -> List[Identifier]:
        return await self.client.endpoints.call(ASSET_UPLOAD_ENDPOINT, assets)

    async def download(self, identifiers: List[Identifier]) -> Files:
        return await self.client.endpoints.call(ASSET_DOWNLOAD_ENDPOINT, identifiers)

    def url(self, identifier: Identifier) -> str:
        address = self.client.network.address
        protocol = "https" if address.secure else "http"
        return f"{protocol}://{address.host}:{address.port}/asset?id={identifier.key()}"

    def proxy(self, url: str) -> str:
        address = self.client.network.address
        protocol = "https" if address.secure else "http"
        return f"{protocol}://{address.host}:{address.port}/proxy?url={url}"

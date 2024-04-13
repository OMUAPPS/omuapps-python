from dataclasses import dataclass
from typing import List

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
from omu.identifier import Identifier
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.serializer import Serializer

ASSET_EXTENSION_TYPE = ExtensionType(
    "asset",
    lambda client: AssetExtension(client),
    lambda: [],
)


@dataclass
class File:
    identifier: Identifier
    buffer: bytes


class FileSerializer:
    @classmethod
    def serialize(cls, item: File) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.identifier.key())
        writer.write_byte_array(item.buffer)
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> File:
        with ByteReader(item) as reader:
            identifier = Identifier.from_key(reader.read_string())
            value = reader.read_byte_array()
        return File(identifier, value)


class FileArraySerializer:
    @classmethod
    def serialize(cls, item: List[File]) -> bytes:
        writer = ByteWriter()
        writer.write_int(len(item))
        for file in item:
            writer.write_string(file.identifier.key())
            writer.write_byte_array(file.buffer)
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> List[File]:
        with ByteReader(item) as reader:
            count = reader.read_int()
            files: List[File] = []
            for _ in range(count):
                identifier = Identifier.from_key(reader.read_string())
                value = reader.read_byte_array()
                files.append(File(identifier, value))
        return files


ASSET_UPLOAD_ENDPOINT = EndpointType[File, Identifier].create_serialized(
    ASSET_EXTENSION_TYPE,
    "upload",
    request_serializer=FileSerializer,
    response_serializer=Serializer.model(Identifier).to_json(),
)
ASSET_UPLOAD_MANY_ENDPOINT = EndpointType[
    List[File], List[Identifier]
].create_serialized(
    ASSET_EXTENSION_TYPE,
    "upload_many",
    request_serializer=FileArraySerializer,
    response_serializer=Serializer.model(Identifier).to_array().to_json(),
)
ASSET_DOWNLOAD_ENDPOINT = EndpointType[Identifier, File].create_serialized(
    ASSET_EXTENSION_TYPE,
    "download",
    request_serializer=Serializer.model(Identifier).to_json(),
    response_serializer=FileSerializer,
)
ASSET_DOWNLOAD_MANY_ENDPOINT = EndpointType[
    List[Identifier], List[File]
].create_serialized(
    ASSET_EXTENSION_TYPE,
    "download_many",
    request_serializer=Serializer.model(Identifier).to_array().to_json(),
    response_serializer=FileArraySerializer,
)


class AssetExtension(Extension):
    def __init__(self, client: Client) -> None:
        self.client = client

    async def upload(self, file: File) -> Identifier:
        return await self.client.endpoints.call(ASSET_UPLOAD_ENDPOINT, file)

    async def upload_many(self, files: List[File]) -> List[Identifier]:
        return await self.client.endpoints.call(ASSET_UPLOAD_MANY_ENDPOINT, files)

    async def download(self, identifier: Identifier) -> File:
        return await self.client.endpoints.call(ASSET_DOWNLOAD_ENDPOINT, identifier)

    async def download_many(self, identifiers: List[Identifier]) -> List[File]:
        return await self.client.endpoints.call(
            ASSET_DOWNLOAD_MANY_ENDPOINT, identifiers
        )

    def url(self, identifier: Identifier) -> str:
        address = self.client.network.address
        protocol = "https" if address.secure else "http"
        return f"{protocol}://{address.host}:{address.port}/asset?id={identifier.key()}"

    def proxy(self, url: str) -> str:
        address = self.client.network.address
        protocol = "https" if address.secure else "http"
        return f"{protocol}://{address.host}:{address.port}/proxy?url={url}"

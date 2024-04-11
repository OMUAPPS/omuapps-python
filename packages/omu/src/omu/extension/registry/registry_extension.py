from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
from omu.helper import Coro
from omu.identifier import Identifier
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.network.packet import PacketType
from omu.serializer import Serializable, SerializeError, Serializer

from .registry import Registry, RegistryType

REGISTRY_EXTENSION_TYPE = ExtensionType(
    "registry",
    lambda client: RegistryExtension(client),
    lambda: [],
)


@dataclass(frozen=True)
class RegistryPacket:
    identifier: Identifier
    value: bytes | None


class REGISTRY_DATA_SERIALIZER:
    @classmethod
    def serialize(cls, item: RegistryPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.identifier.key())
        writer.write_boolean(item.value is not None)
        if item.value is not None:
            writer.write_byte_array(item.value)
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> RegistryPacket:
        with ByteReader(item) as reader:
            key = Identifier.from_key(reader.read_string())
            existing = reader.read_boolean()
            value = reader.read_byte_array() if existing else None
        return RegistryPacket(key, value)


REGISTRY_UPDATE_PACKET = PacketType[RegistryPacket].create_serialized(
    REGISTRY_EXTENSION_TYPE,
    "update",
    serializer=REGISTRY_DATA_SERIALIZER,
)
REGISTRY_LISTEN_PACKET = PacketType[Identifier].create_json(
    REGISTRY_EXTENSION_TYPE,
    "listen",
    Serializer.model(Identifier),
)
REGISTRY_GET_ENDPOINT = EndpointType[Identifier, RegistryPacket].create_serialized(
    REGISTRY_EXTENSION_TYPE,
    "get",
    request_serializer=Serializer.model(Identifier).to_json(),
    response_serializer=REGISTRY_DATA_SERIALIZER,
)


class RegistryExtension(Extension):
    def __init__(self, client: Client) -> None:
        self.client = client
        client.network.register_packet(REGISTRY_UPDATE_PACKET)

    def get[T](self, registry_type: RegistryType[T]) -> Registry[T]:
        return RegistryImpl(
            self.client,
            registry_type.identifier,
            registry_type.default_value,
            registry_type.serializer,
        )

    def create[T](self, name: str, default_value: T) -> Registry[T]:
        identifier = self.client.app.identifier / name
        return RegistryImpl(self.client, identifier, default_value, Serializer.json())


class RegistryImpl[T](Registry[T]):
    def __init__(
        self,
        client: Client,
        identifier: Identifier,
        default_value: T,
        serializer: Serializable[T, bytes],
    ) -> None:
        self.client = client
        self.identifier = identifier
        self.default_value = default_value
        self.serializer = serializer
        self.listeners: List[Coro[[T], None]] = []
        self.listening = False
        client.network.add_packet_handler(REGISTRY_UPDATE_PACKET, self._on_update)

    async def get(self) -> T:
        result = await self.client.endpoints.call(
            REGISTRY_GET_ENDPOINT, self.identifier
        )
        if result.value is None:
            return self.default_value
        try:
            return self.serializer.deserialize(result.value)
        except SerializeError as e:
            raise SerializeError(
                f"Failed to deserialize registry value for identifier {self.identifier}"
            ) from e

    async def update(self, handler: Coro[[T], T]) -> None:
        value = await self.get()
        new_value = await handler(value)
        await self.client.send(
            REGISTRY_UPDATE_PACKET,
            RegistryPacket(
                identifier=self.identifier,
                value=self.serializer.serialize(new_value),
            ),
        )

    def listen(self, handler: Coro[[T], None]) -> Callable[[], None]:
        if not self.listening:
            self.client.network.add_task(
                lambda: self.client.send(REGISTRY_LISTEN_PACKET, self.identifier)
            )
            self.listening = True

        self.listeners.append(handler)
        return lambda: self.listeners.remove(handler)

    async def _on_update(self, event: RegistryPacket) -> None:
        if event.identifier != self.identifier:
            return
        if event.value is not None:
            try:
                value = self.serializer.deserialize(event.value)
            except SerializeError as e:
                raise SerializeError(
                    f"Failed to deserialize registry value for identifier {self.identifier}"
                ) from e
        else:
            value = self.default_value
        for listener in self.listeners:
            await listener(value)

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.helper import Coro
from omu.identifier import Identifier
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.network.packet import PacketType
from omu.serializer import Serializable

from .message import Message, MessageType

MESSAGE_EXTENSION_TYPE = ExtensionType(
    "message",
    lambda client: MessageExtension(client),
    lambda: [],
)


@dataclass
class MessageData:
    key: str
    body: bytes


class MessageSerializer(Serializable[MessageData, bytes]):
    def serialize(self, item: MessageData) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.key)
        writer.write_byte_array(item.body)
        return writer.finish()

    def deserialize(self, item: bytes) -> MessageData:
        with ByteReader(item) as reader:
            key = reader.read_string()
            body = reader.read_byte_array()
        return MessageData(key=key, body=body)


MESSAGE_LISTEN_PACKET = PacketType[str].create_json(MESSAGE_EXTENSION_TYPE, "listen")
MESSAGE_BROADCAST_PACKET = PacketType[MessageData].create_serialized(
    MESSAGE_EXTENSION_TYPE,
    "broadcast",
    MessageSerializer(),
)


class MessageExtension(Extension):
    def __init__(self, client: Client):
        self.client = client
        self._message_identifiers: List[Identifier] = []
        client.network.register_packet(
            MESSAGE_LISTEN_PACKET,
            MESSAGE_BROADCAST_PACKET,
        )

    def create[T](self, name: str, _t: type[T] | None = None) -> Message[T]:
        identifier = self.client.app.identifier / name
        if identifier in self._message_identifiers:
            raise Exception(f"Message {identifier} already exists")
        self._message_identifiers.append(identifier)
        type = MessageType.create_json(identifier, name)
        return MessageImpl(self.client, type)

    def get[T](self, message_type: MessageType[T]) -> Message[T]:
        return MessageImpl(self.client, message_type)


class MessageImpl[T](Message):
    def __init__(self, client: Client, message_type: MessageType[T]):
        self.client = client
        self.key = message_type.identifier.key()
        self.serializer = message_type.serializer
        self.listeners = []
        self.listening = False
        client.network.add_packet_handler(MESSAGE_BROADCAST_PACKET, self._on_broadcast)

    async def broadcast(self, body: T) -> None:
        data = self.serializer.serialize(body)
        await self.client.send(
            MESSAGE_BROADCAST_PACKET,
            MessageData(key=self.key, body=data),
        )

    def listen(self, listener: Coro[[T], None]) -> Callable[[], None]:
        self.listeners.append(listener)
        if not self.listening:
            self.client.network.add_task(self._listen)
            self.listening = True
        return lambda: self.listeners.remove(listener)

    async def _listen(self) -> None:
        await self.client.send(MESSAGE_LISTEN_PACKET, self.key)

    async def _on_broadcast(self, data: MessageData) -> None:
        if data.key != self.key:
            return
        for listener in self.listeners:
            await listener(data.body)

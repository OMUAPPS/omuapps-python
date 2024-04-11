from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.helper import Coro
from omu.identifier import Identifier
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.network.packet import PacketType
from omu.serializer import Serializer

from .message import Message, MessageType

MESSAGE_EXTENSION_TYPE = ExtensionType(
    "message",
    lambda client: MessageExtension(client),
    lambda: [],
)


@dataclass
class MessagePacket:
    id: Identifier
    body: bytes


class MessageSerializer:
    @classmethod
    def serialize(cls, item: MessagePacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.id.key())
        writer.write_byte_array(item.body)
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> MessagePacket:
        with ByteReader(item) as reader:
            key = Identifier.from_key(reader.read_string())
            body = reader.read_byte_array()
        return MessagePacket(id=key, body=body)


MESSAGE_LISTEN_PACKET = PacketType[Identifier].create_json(
    MESSAGE_EXTENSION_TYPE,
    "listen",
    serializer=Serializer.model(Identifier),
)
MESSAGE_BROADCAST_PACKET = PacketType[MessagePacket].create_serialized(
    MESSAGE_EXTENSION_TYPE,
    "broadcast",
    MessageSerializer,
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
        self.identifier = message_type.identifier
        self.serializer = message_type.serializer
        self.listeners = []
        self.listening = False
        client.network.add_packet_handler(MESSAGE_BROADCAST_PACKET, self._on_broadcast)

    async def broadcast(self, body: T) -> None:
        data = self.serializer.serialize(body)
        await self.client.send(
            MESSAGE_BROADCAST_PACKET,
            MessagePacket(id=self.identifier, body=data),
        )

    def listen(self, listener: Coro[[T], None]) -> Callable[[], None]:
        if not self.listening:
            self.client.network.add_task(self._send_listen)
            self.listening = True

        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)

    async def _send_listen(self) -> None:
        await self.client.send(MESSAGE_LISTEN_PACKET, self.identifier)

    async def _on_broadcast(self, data: MessagePacket) -> None:
        if data.id != self.identifier:
            return

        body = self.serializer.deserialize(data.body)
        for listener in self.listeners:
            await listener(body)

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

from .signal import Signal, SignalType

SIGNAL_EXTENSION_TYPE = ExtensionType(
    name="signal",
    create=lambda client: SignalExtension(client),
    dependencies=lambda: [],
)


@dataclass
class SignalPacket:
    id: Identifier
    body: bytes


class SignalSerializer:
    @classmethod
    def serialize(cls, item: SignalPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.id.key())
        writer.write_byte_array(item.body)
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> SignalPacket:
        with ByteReader(item) as reader:
            key = Identifier.from_key(reader.read_string())
            body = reader.read_byte_array()
        return SignalPacket(id=key, body=body)


SIGNAL_LISTEN_PACKET = PacketType[Identifier].create_json(
    SIGNAL_EXTENSION_TYPE,
    "listen",
    serializer=Serializer.pydantic(Identifier),
)
SIGNAL_BROADCAST_PACKET = PacketType[SignalPacket].create_serialized(
    SIGNAL_EXTENSION_TYPE,
    "broadcast",
    SignalSerializer,
)


class SignalExtension(Extension):
    def __init__(self, client: Client):
        self.client = client
        self.signals: List[Identifier] = []
        client.network.register_packet(
            SIGNAL_LISTEN_PACKET,
            SIGNAL_BROADCAST_PACKET,
        )

    def create[T](self, name: str, _t: type[T] | None = None) -> Signal[T]:
        identifier = self.client.app.identifier / name
        if identifier in self.signals:
            raise Exception(f"Signal {identifier} already exists")
        self.signals.append(identifier)
        type = SignalType.create_json(identifier, name)
        return SignalImpl(self.client, type)

    def get[T](self, signal_type: SignalType[T]) -> Signal[T]:
        return SignalImpl(self.client, signal_type)


class SignalImpl[T](Signal):
    def __init__(self, client: Client, signal_type: SignalType[T]):
        self.client = client
        self.identifier = signal_type.identifier
        self.serializer = signal_type.serializer
        self.listeners = []
        self.listening = False
        client.network.add_packet_handler(SIGNAL_BROADCAST_PACKET, self._on_broadcast)

    async def broadcast(self, body: T) -> None:
        data = self.serializer.serialize(body)
        await self.client.send(
            SIGNAL_BROADCAST_PACKET,
            SignalPacket(id=self.identifier, body=data),
        )

    def listen(self, listener: Coro[[T], None]) -> Callable[[], None]:
        if not self.listening:
            self.client.network.add_task(self._send_listen)
            self.listening = True

        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)

    async def _send_listen(self) -> None:
        await self.client.send(SIGNAL_LISTEN_PACKET, self.identifier)

    async def _on_broadcast(self, data: SignalPacket) -> None:
        if data.id != self.identifier:
            return

        body = self.serializer.deserialize(data.body)
        for listener in self.listeners:
            await listener(body)

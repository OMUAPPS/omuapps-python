from __future__ import annotations

from typing import Callable, Dict

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.helper import Coro
from omu.identifier import Identifier
from omu.network.packet import PacketType
from omu.serializer import Serializer

from .packets import SignalPacket, SignalRegisterPacket
from .signal import Signal, SignalType

SIGNAL_EXTENSION_TYPE = ExtensionType(
    "signal",
    lambda client: SignalExtension(client),
    lambda: [],
)


SIGNAL_LISTEN_PACKET = PacketType[Identifier].create_json(
    SIGNAL_EXTENSION_TYPE,
    "listen",
    serializer=Serializer.model(Identifier),
)
SIGNAL_NOTIFY_PACKET = PacketType[SignalPacket].create_serialized(
    SIGNAL_EXTENSION_TYPE,
    "notify",
    SignalPacket,
)
SIGNAL_REGISTER_PACKET = PacketType[SignalRegisterPacket].create_serialized(
    SIGNAL_EXTENSION_TYPE,
    "register",
    SignalRegisterPacket,
)


class SignalExtension(Extension):
    def __init__(self, client: Client):
        self.client = client
        self.signals: Dict[Identifier, Signal] = {}
        client.network.register_packet(
            SIGNAL_REGISTER_PACKET,
            SIGNAL_LISTEN_PACKET,
            SIGNAL_NOTIFY_PACKET,
        )

    def create_signal[T](self, signal_type: SignalType[T]) -> Signal[T]:
        if signal_type.identifier in self.signals:
            raise Exception(f"Signal {signal_type.identifier} already exists")
        return SignalImpl(self.client, signal_type)

    def create[T](self, name: str, _t: type[T] | None = None) -> Signal[T]:
        identifier = self.client.app.id / name
        type = SignalType[T].create_json(
            identifier,
            name,
        )
        return self.create_signal(type)

    def get[T](self, signal_type: SignalType[T]) -> Signal[T]:
        return self.create_signal(signal_type)


class SignalImpl[T](Signal):
    def __init__(self, client: Client, signal_type: SignalType[T]):
        self.client = client
        self.identifier = signal_type.identifier
        self.serializer = signal_type.serializer
        self.listeners = []
        self.listening = False
        client.network.add_packet_handler(SIGNAL_NOTIFY_PACKET, self._on_broadcast)

    async def send(self, body: T) -> None:
        data = self.serializer.serialize(body)
        await self.client.send(
            SIGNAL_NOTIFY_PACKET,
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

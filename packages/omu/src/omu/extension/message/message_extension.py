from __future__ import annotations

from typing import Any, TypedDict

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.helper import Coro
from omu.identifier import Identifier
from omu.network.packet import JsonPacketType

from .message import Message

MessageExtensionType = ExtensionType(
    "message",
    lambda client: MessageExtension(client),
    lambda: [],
)


class MessageData(TypedDict):
    key: str
    body: Any


MessageRegisterPacket = JsonPacketType[str].of_extension(
    MessageExtensionType, "register"
)
MessageListenPacket = JsonPacketType[str].of_extension(MessageExtensionType, "listen")
MessageBroadcastPacket = JsonPacketType[MessageData].of_extension(
    MessageExtensionType, "broadcast"
)


class MessageExtension(Extension):
    def __init__(self, client: Client):
        self.client = client
        self._listen_keys: set[str] = set()
        self._keys: set[str] = set()
        client.network.register_packet(
            MessageRegisterPacket,
            MessageListenPacket,
            MessageBroadcastPacket,
        )

    def create[T](self, name: str, _t: type[T] | None = None) -> Message[T]:
        identifier = self.client.app.identifier / name
        return MessageImpl(self.client, identifier)

    def get(self, identifier: Identifier) -> Message:
        return MessageImpl(self.client, identifier)


class MessageImpl[T](Message):
    def __init__(self, client: Client, identifier: Identifier):
        self.client = client
        self.identifier = identifier
        self.key = identifier.key()
        self.listeners = []
        self.listening = False
        client.network.add_packet_handler(MessageBroadcastPacket, self._on_broadcast)

    async def broadcast(self, body: T) -> None:
        await self.client.send(
            MessageBroadcastPacket,
            MessageData(key=self.key, body=body),
        )

    def listen(self, listener: Coro[[T], None]) -> None:
        self.listeners.append(listener)
        if not self.listening:
            self.client.network.add_task(self._listen)
            self.listening = True

    async def _listen(self) -> None:
        await self.client.send(MessageListenPacket, self.key)

    async def _on_broadcast(self, data: MessageData) -> None:
        if data["key"] != self.key:
            return
        for listener in self.listeners:
            await listener(data["body"])

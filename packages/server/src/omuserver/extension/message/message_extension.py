from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from omu.extension.message.message_extension import (
    MessageBroadcastEvent,
    MessageEventData,
    MessageListenEvent,
    MessageRegisterEvent,
)
from omuserver.extension import Extension

if TYPE_CHECKING:
    from omuserver import Server
    from omuserver.session.session import Session


class Message:
    def __init__(self, key: str) -> None:
        self.key = key
        self.listeners: set[Session] = set()

    def add_listener(self, session: Session) -> None:
        self.listeners.add(session)
        session.listeners.disconnected += self.handle_disconnected_session

    async def handle_disconnected_session(self, session: Session) -> None:
        self.listeners.discard(session)


class MessageExtension(Extension):
    def __init__(self, server: Server):
        self._server = server
        self._keys: Dict[str, Message] = {}
        server.packet_dispatcher.register(
            MessageRegisterEvent, MessageListenEvent, MessageBroadcastEvent
        )
        server.packet_dispatcher.add_packet_handler(
            MessageRegisterEvent, self._on_register
        )
        server.packet_dispatcher.add_packet_handler(MessageListenEvent, self._on_listen)
        server.packet_dispatcher.add_packet_handler(
            MessageBroadcastEvent, self._on_broadcast
        )

    @classmethod
    def create(cls, server):
        return cls(server)

    async def _on_register(self, session: Session, key: str) -> None:
        if key in self._keys:
            return
        self._keys[key] = Message(key)

    def has(self, key):
        return key in self._keys

    async def _on_listen(self, session: Session, key: str) -> None:
        if key not in self._keys:
            self._keys[key] = Message(key)
        message = self._keys[key]
        message.add_listener(session)

    async def _on_broadcast(self, session: Session, data: MessageEventData) -> None:
        key = data["key"]
        if key not in self._keys:
            self._keys[key] = Message(key)
        message = self._keys[key]
        for listener in message.listeners:
            await listener.send(MessageBroadcastEvent, data)

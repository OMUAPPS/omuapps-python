from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from omu.extension.message.message_extension import (
    MESSAGE_BROADCAST_PACKET,
    MESSAGE_LISTEN_PACKET,
    MessageData,
)

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


class MessageExtension:
    def __init__(self, server: Server):
        self._server = server
        self._keys: Dict[str, Message] = {}
        server.packet_dispatcher.register(
            MESSAGE_LISTEN_PACKET, MESSAGE_BROADCAST_PACKET
        )
        server.packet_dispatcher.add_packet_handler(
            MESSAGE_LISTEN_PACKET, self._on_listen
        )
        server.packet_dispatcher.add_packet_handler(
            MESSAGE_BROADCAST_PACKET, self._on_broadcast
        )

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

    async def _on_broadcast(self, session: Session, data: MessageData) -> None:
        key = data.key
        if key not in self._keys:
            self._keys[key] = Message(key)
        message = self._keys[key]
        for listener in message.listeners:
            await listener.send(MESSAGE_BROADCAST_PACKET, data)

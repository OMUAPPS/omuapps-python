from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from omu.extension.message.message_extension import (
    MessageBroadcastEvent,
    MessageEventData,
    MessageListenEvent,
    MessageRegisterEvent,
)

from omuserver.extension import Extension
from omuserver.session.session import SessionListener

if TYPE_CHECKING:
    from omuserver import Server
    from omuserver.session.session import Session


class Message(SessionListener):
    def __init__(self, key: str, session: Session | None = None) -> None:
        self.key = key
        self.session: Session | None = session
        self.listeners: set[Session] = set()

    def add_listener(self, session: Session) -> None:
        self.listeners.add(session)
        session.add_listener(self)

    def set_session(self, session: Session) -> None:
        if self.session is not None and not self.session.closed:
            raise Exception("Session already set")
        self.session = session

    async def on_disconnected(self, session: Session) -> None:
        self.listeners.discard(session)


class MessageExtension(Extension):
    def __init__(self, server: Server):
        self._server = server
        self._keys: Dict[str, Message] = {}
        server.events.register(
            MessageRegisterEvent, MessageListenEvent, MessageBroadcastEvent
        )
        server.events.add_listener(MessageRegisterEvent, self._on_register)
        server.events.add_listener(MessageListenEvent, self._on_listen)
        server.events.add_listener(MessageBroadcastEvent, self._on_broadcast)

    @classmethod
    def create(cls, server):
        return cls(server)

    async def _on_register(self, session: Session, key: str) -> None:
        if self.has(key):
            message = self._keys[key]
            message.set_session(session)
            return
        self._keys[key] = Message(key, session)

    def has(self, key):
        return key in self._keys

    async def _on_listen(self, session: Session, key: str) -> None:
        if key not in self._keys:
            self._keys[key] = Message(key)
        message = self._keys[key]
        message.add_listener(session)

    async def _on_broadcast(self, session: Session, data: MessageEventData) -> None:
        key = data["key"]
        message = self._keys[key]
        if message.session != session:
            raise Exception("Unauthorized broadcast")
        for listener in message.listeners:
            await listener.send(MessageBroadcastEvent, data)

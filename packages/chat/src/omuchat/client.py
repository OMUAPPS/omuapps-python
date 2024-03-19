from typing import Callable

from omu import Address, App, OmuClient

from omuchat.event import EventRegistry, EventSource
from omuchat.event.event import EventHandler

from .chat import (
    AuthorsTableKey,
    ChannelsTableKey,
    Chat,
    MessagesTableKey,
    ProviderTableKey,
    RoomTableKey,
)


class Client(OmuClient):
    def __init__(
        self,
        app: App,
        address: Address | None = None,
    ):
        self.address = address or Address("127.0.0.1", 26423)
        super().__init__(
            app=app,
            address=self.address,
        )
        self.chat = Chat(self)
        self.messages = self.tables.get(MessagesTableKey)
        self.authors = self.tables.get(AuthorsTableKey)
        self.channels = self.tables.get(ChannelsTableKey)
        self.providers = self.tables.get(ProviderTableKey)
        self.rooms = self.tables.get(RoomTableKey)
        self.event_registry = EventRegistry(self)

    def on[**P](
        self, event: EventSource[P]
    ) -> Callable[[EventHandler[P]], EventHandler[P]]:
        def decorator(listener: EventHandler[P]) -> EventHandler[P]:
            self.event_registry.register(event, listener)
            return listener

        return decorator

    def off[**P](
        self, event: EventSource[P]
    ) -> Callable[[EventHandler[P]], EventHandler[P]]:
        def decorator(listener: EventHandler[P]) -> EventHandler[P]:
            self.event_registry.unregister(event, listener)
            return listener

        return decorator

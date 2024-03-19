from typing import Callable

from omu import Address, App, OmuClient

from .chat import (
    AuthorsTableKey,
    ChannelsTableKey,
    Chat,
    MessagesTableKey,
    ProviderTableKey,
    RoomTableKey,
)
from .event import EventHandler, EventKey, EventRegistry, events


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
        self.event_registry = EventRegistry()
        self.chat = Chat(self)
        self.messages = self.tables.get(MessagesTableKey)
        self.authors = self.tables.get(AuthorsTableKey)
        self.channels = self.tables.get(ChannelsTableKey)
        self.providers = self.tables.get(ProviderTableKey)
        self.rooms = self.tables.get(RoomTableKey)
        self.network.listeners.connected += self.on_connected

    async def on_connected(self) -> None:
        await self.event_registry.dispatch(events.Ready)

    def on[**P](self, key: EventKey[P]) -> Callable[[EventHandler[P]], EventHandler[P]]:
        def decorator(func: EventHandler[P]) -> EventHandler[P]:
            self.event_registry.add(key, func)
            return func

        return decorator

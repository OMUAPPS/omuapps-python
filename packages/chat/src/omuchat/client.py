from collections.abc import Callable

from omu import Address, App, OmuClient

from omuchat.event import EventHandler, EventRegistry, EventSource

from .chat import Chat


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
        self.event_registry = EventRegistry(self)

    def on[**P](
        self, event: EventSource[P]
    ) -> Callable[[EventHandler[P]], EventHandler[P]]:
        def decorator(listener: EventHandler[P]) -> EventHandler[P]:
            self.event_registry.register(event, listener)
            return listener

        return decorator

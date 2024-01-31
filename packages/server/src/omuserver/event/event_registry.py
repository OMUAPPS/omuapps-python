from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, List

from loguru import logger

from omuserver.network.network import NetworkListener
from omuserver.session.session import Session, SessionListener

if TYPE_CHECKING:
    from omu.event import EventData, EventType

    from omuserver.server import Server


type EventCallback[T] = Callable[[Session, T], Coroutine[Any, Any, None]]


class EventEntry[T]:
    def __init__(
        self,
        event_type: EventType[T],
        listeners: List[EventCallback[T]],
    ):
        self.event_type = event_type
        self.listeners = listeners


class EventRegistry(NetworkListener, SessionListener):
    def __init__(self, server: Server):
        self._server = server
        self._events: Dict[str, EventEntry] = {}
        server.network.add_listener(self)

    async def on_connected(self, session: Session) -> None:
        session.add_listener(self)

    async def on_event(self, session: Session, event_data: EventData) -> None:
        event = self._events.get(event_data.type)
        if not event:
            logger.warning(f"Received unknown event type {event_data.type}")
            return
        data = event.event_type.serializer.deserialize(event_data.data)
        for listener in event.listeners:
            await listener(session, data)

    def register(self, *types: EventType) -> None:
        for type in types:
            if self._events.get(type.type):
                raise ValueError(f"Event type {type.type} already registered")
            self._events[type.type] = EventEntry(type, [])

    def add_listener[T](
        self,
        event_type: EventType[T],
        listener: EventCallback[T] | None = None,
    ) -> Callable[[EventCallback[T]], None]:
        if not self._events.get(event_type.type):
            raise ValueError(f"Event type {event_type.type} not registered")

        def decorator(listener: EventCallback[T]) -> None:
            self._events[event_type.type].listeners.append(listener)

        if listener:
            decorator(listener)
        return decorator

    def remove_listener(
        self, event_type: EventType, listener: EventCallback[Any]
    ) -> None:
        if not self._events.get(event_type.type):
            raise ValueError(f"Event type {event_type.type} not registered")
        self._events[event_type.type].listeners.remove(listener)

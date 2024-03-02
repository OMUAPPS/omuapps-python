from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Awaitable, Callable, Dict, List

from loguru import logger

from omu.network import ConnectionListener

if TYPE_CHECKING:
    from omu.client import Client
    from omu.event import EventData, EventType


type EventListener[T] = Callable[[T], Awaitable[None]]


class EventRegistry(abc.ABC):
    @abc.abstractmethod
    def register(self, *types: EventType) -> None:
        ...

    @abc.abstractmethod
    def add_listener[T](
        self,
        event_type: EventType[T],
        listener: EventListener[T] | None = None,
    ) -> Callable[[EventListener[T]], None]:
        ...

    @abc.abstractmethod
    def remove_listener(
        self, event_type: EventType, listener: Callable[[bytes], None]
    ) -> None:
        ...


class EventEntry[T]:
    def __init__(
        self,
        event_type: EventType[T],
        listeners: List[EventListener[T]],
    ):
        self.event_type = event_type
        self.listeners = listeners


class EventRegistryImpl(EventRegistry, ConnectionListener):
    def __init__(self, client: Client):
        client.connection.add_listener(self)
        self._events: Dict[str, EventEntry] = {}
        self._own_events: Dict[str, EventEntry] = {}

    def register(self, *types: EventType) -> None:
        for type in types:
            if self._events.get(type.type):
                raise ValueError(f"Event type {type.type} already registered")
            self._events[type.type] = EventEntry(type, [])

    def add_listener[T](
        self,
        event_type: EventType[T],
        listener: EventListener[T] | None = None,
    ) -> Callable[[EventListener[T]], None]:
        if not self._events.get(event_type.type):
            raise ValueError(f"Event type {event_type.type} not registered")

        def decorator(listener: EventListener[T]) -> None:
            self._events[event_type.type].listeners.append(listener)

        if listener:
            decorator(listener)
        return decorator

    def remove_listener(self, event_type: EventType, listener: EventListener) -> None:
        if not self._events.get(event_type.type):
            raise ValueError(f"Event type {event_type.type} not registered")
        self._events[event_type.type].listeners.remove(listener)

    async def on_event(self, event_data: EventData) -> None:
        event = self._events.get(event_data.type)
        if not event:
            logger.warning(f"Received unknown event type {event_data.type}")
            return
        data = event.event_type.serializer.deserialize(event_data.data)
        for listener in event.listeners:
            await listener(data)

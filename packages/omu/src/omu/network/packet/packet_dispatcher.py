from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Awaitable, Callable, Dict, List

from loguru import logger

from omu.network import ConnectionListener

if TYPE_CHECKING:
    from omu.client import Client
    from omu.network.packet import PacketData, PacketType


type EventListener[T] = Callable[[T], Awaitable[None]]


class PacketDispatcher(abc.ABC):
    @abc.abstractmethod
    def register(self, *types: PacketType) -> None: ...

    @abc.abstractmethod
    def add_listener[T](
        self,
        event_type: PacketType[T],
        listener: EventListener[T] | None = None,
    ) -> Callable[[EventListener[T]], None]: ...

    @abc.abstractmethod
    def remove_listener(
        self, event_type: PacketType, listener: Callable[[bytes], None]
    ) -> None: ...


class PacketListeners[T]:
    def __init__(
        self,
        event_type: PacketType[T],
        listeners: List[EventListener[T]],
    ):
        self.event_type = event_type
        self.listeners = listeners


class PacketDispatcherImpl(PacketDispatcher, ConnectionListener):
    def __init__(self, client: Client):
        client.connection.add_listener(self)
        self._packet_listeners: Dict[str, PacketListeners] = {}

    def register(self, *packet_types: PacketType) -> None:
        for packet in packet_types:
            if self._packet_listeners.get(packet.type):
                raise ValueError(f"Event type {packet.type} already registered")
            self._packet_listeners[packet.type] = PacketListeners(packet, [])

    def add_listener[T](
        self,
        event_type: PacketType[T],
        listener: EventListener[T] | None = None,
    ) -> Callable[[EventListener[T]], None]:
        if not self._packet_listeners.get(event_type.type):
            raise ValueError(f"Event type {event_type.type} not registered")

        def decorator(listener: EventListener[T]) -> None:
            self._packet_listeners[event_type.type].listeners.append(listener)

        if listener:
            decorator(listener)
        return decorator

    def remove_listener(self, event_type: PacketType, listener: EventListener) -> None:
        if not self._packet_listeners.get(event_type.type):
            raise ValueError(f"Event type {event_type.type} not registered")
        self._packet_listeners[event_type.type].listeners.remove(listener)

    async def on_event(self, event_data: PacketData) -> None:
        event = self._packet_listeners.get(event_data.type)
        if not event:
            logger.warning(f"Received unknown event type {event_data.type}")
            return
        data = event.event_type.serializer.deserialize(event_data.data)
        for listener in event.listeners:
            await listener(data)

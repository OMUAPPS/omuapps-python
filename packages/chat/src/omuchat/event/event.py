from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Coroutine, Dict, Mapping

from omu.event_emitter import EventEmitter

if TYPE_CHECKING:
    from omu.extension.table import Table

    from omuchat.client import Client

type EventHandler[**P] = Callable[P, Coroutine[None, None, None]]


@dataclass(frozen=True)
class EventSource[**P]:
    subscribe: Callable[[EventHandler[P], Client]]
    unsubscribe: Callable[[EventHandler[P], Client]]


class ListenerEvent[**P](EventSource[P]):
    def __init__(self, get_listener: Callable[[Client], EventEmitter[P]]):
        super().__init__(self._subscribe, self._unsubscribe)
        self.get_listener = get_listener

    def _subscribe(
        self,
        emit: EventHandler[P],
        client: Client,
    ):
        listener = self.get_listener(client)
        listener += emit

    def _unsubscribe(
        self,
        emit: EventHandler[P],
        client: Client,
    ):
        listener = self.get_listener(client)
        listener -= emit


class TableEvent[T](ListenerEvent[Mapping[str, T]]):
    def __init__(self, get_table: Callable[[Client], Table[T]]):
        self.get_table = get_table
        super().__init__(
            lambda client: get_table(client).listeners.cache_update,
        )
        self.add_batch = ListenerEvent(
            lambda client: get_table(client).listeners.add,
        )
        self.update_batch = ListenerEvent(
            lambda client: get_table(client).listeners.update,
        )
        self.remove_batch = ListenerEvent(
            lambda client: get_table(client).listeners.remove,
        )
        self.add = self._create_batch_subscriber(
            lambda table: table.listeners.add,
        )
        self.update = self._create_batch_subscriber(
            lambda table: table.listeners.update,
        )
        self.remove = self._create_batch_subscriber(
            lambda table: table.listeners.remove,
        )
        self.clear = ListenerEvent(
            lambda client: get_table(client).listeners.clear,
        )
        self.wrappers = {}

    def _create_batch_wrapper(self, emit: EventHandler[[T]]):
        async def wrapper(items: Mapping[str, T]):
            for item in items.values():
                await emit(item)

        return wrapper

    def _create_batch_subscriber(
        self, get_listener: Callable[[Table[T]], EventEmitter[Mapping[str, T]]]
    ):
        batch_wrapper: EventHandler[Mapping[str, T]] | None = None

        def subscribe(emit: EventHandler[T], client: Client):
            listener = get_listener(self.get_table(client))
            nonlocal batch_wrapper
            batch_wrapper = self._create_batch_wrapper(emit)
            listener += batch_wrapper

        def unsubscribe(emit: EventHandler[T], client: Client):
            if batch_wrapper is None:
                raise ValueError("Listener not subscribed")
            listener = get_listener(self.get_table(client))
            listener -= batch_wrapper

        return EventSource(subscribe, unsubscribe)


@dataclass(frozen=True)
class Entry[**P]:
    source: EventSource[P]
    listeners: EventEmitter[P]


class EventRegistry:
    def __init__(self, client: Client):
        self.client = client
        self.events: Dict[int, Entry] = {}

    def register[**P](self, event: EventSource[P], listener: EventHandler[P]):
        event_id = id(event)
        if event_id not in self.events:
            entry = Entry[P](event, EventEmitter[P]())
            event.subscribe(entry.listeners.emit, self.client)
            self.events[event_id] = entry  # type: ignore
        self.events[event_id].listeners.subscribe(listener)

    def unregister[**P](self, event: EventSource[P], listener: EventHandler[P]):
        event_id = id(event)
        if event_id not in self.events:
            return
        entry = self.events[event_id]
        entry.listeners.unsubscribe(listener)
        if entry.listeners.empty:
            entry.source.unsubscribe(entry.listeners.emit, self.client)
            del entry

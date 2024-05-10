from __future__ import annotations

from collections.abc import Callable, Coroutine, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from omu.event_emitter import EventEmitter, Unlisten
from omu.extension.table import Table

if TYPE_CHECKING:
    from omuchat.client import Client

type EventHandler[**P] = Callable[P, Coroutine[None, None, None]]


@dataclass(frozen=True)
class EventSource[**P]:
    listen: Callable[[EventHandler[P], Client], Unlisten]


class ListenerEvent[**P](EventSource[P]):
    def __init__(self, get_listener: Callable[[Client], EventEmitter[P]]):
        super().__init__(self._subscribe)
        self.get_listener = get_listener

    def _subscribe(
        self,
        emit: EventHandler[P],
        client: Client,
    ):
        listener = self.get_listener(client)
        return listener.listen(emit)


class TableEvent[T](ListenerEvent[Mapping[str, T]]):
    def __init__(self, get_table: Callable[[Client], Table[T]]):
        self.get_table = get_table
        super().__init__(
            lambda client: get_table(client).event.cache_update,
        )
        self.add_batch = ListenerEvent(
            lambda client: get_table(client).event.add,
        )
        self.update_batch = ListenerEvent(
            lambda client: get_table(client).event.update,
        )
        self.remove_batch = ListenerEvent(
            lambda client: get_table(client).event.remove,
        )
        self.add = self._create_batch_subscriber(
            lambda table: table.event.add,
        )
        self.update = self._create_batch_subscriber(
            lambda table: table.event.update,
        )
        self.remove = self._create_batch_subscriber(
            lambda table: table.event.remove,
        )
        self.clear = ListenerEvent(
            lambda client: get_table(client).event.clear,
        )
        self.wrappers = {}

    @staticmethod
    def _create_batch_wrapper(emit: EventHandler[[T]]):
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
            return listener.listen(batch_wrapper)

        return EventSource(subscribe)


@dataclass(frozen=True)
class Entry[**P]:
    source: EventSource[P]
    listeners: EventEmitter[P]


class EventRegistry:
    def __init__(self, client: Client):
        self.client = client
        self.events: dict[int, Entry] = {}

    def register[**P](
        self, event: EventSource[P], listener: EventHandler[P]
    ) -> Unlisten:
        event_id = id(event)
        if event_id not in self.events:
            entry = Entry[P](event, EventEmitter[P]())
            event.listen(entry.listeners.emit, self.client)
            self.events[event_id] = entry  # type: ignore
        return self.events[event_id].listeners.listen(listener)

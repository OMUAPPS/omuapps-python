from __future__ import annotations

import asyncio
from typing import Callable, List, Self

from omu.helper import Coro


class EventEmitter[**P]:
    def __init__(
        self,
        on_subscribe: Callable[[], None] | Coro[[], None] | None = None,
        on_empty: Callable[[], None] | Coro[[], None] | None = None,
    ) -> None:
        self.on_subscribe = on_subscribe
        self.on_empty = on_empty
        self._listeners: List[Coro[P, None]] = []

    @property
    def empty(self) -> bool:
        return len(self._listeners) == 0

    def subscribe(self, listener: Coro[P, None]) -> None:
        if listener in self._listeners:
            raise ValueError("Listener already subscribed")
        if self.on_subscribe and len(self._listeners) == 0:
            coroutine = self.on_subscribe()
            if asyncio.iscoroutine(coroutine):
                asyncio.create_task(coroutine)
        self._listeners.append(listener)

    def unsubscribe(self, listener: Coro[P, None]) -> None:
        if listener not in self._listeners:
            return
        self._listeners.remove(listener)
        if self.on_empty and len(self._listeners) == 0:
            coroutine = self.on_empty()
            if asyncio.iscoroutine(coroutine):
                asyncio.create_task(coroutine)

    def __iadd__(self, listener: Coro[P, None]) -> Self:
        self.subscribe(listener)
        return self

    def __isub__(self, listener: Coro[P, None]) -> Self:
        self.unsubscribe(listener)
        return self

    async def emit(self, *args: P.args, **kwargs: P.kwargs) -> None:
        for listener in self._listeners:
            await listener(*args, **kwargs)

    __call__ = emit

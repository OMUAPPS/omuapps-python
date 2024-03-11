from __future__ import annotations

from typing import List, Self

from omu.helper import Coro


class EventEmitter[**P]:
    def __init__(self):
        self._listeners: List[Coro[P, None]] = []

    def subscribe(self, listener: Coro[P, None]) -> None:
        if listener in self._listeners:
            raise ValueError("Listener already subscribed")
        self._listeners.append(listener)

    def unsubscribe(self, listener: Coro[P, None]) -> None:
        self._listeners.remove(listener)

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

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Awaitable, Callable

if TYPE_CHECKING:
    from omuserver.session import Session

type Coro[**P, R] = Callable[P, Awaitable[R]]


class Network(abc.ABC):
    @abc.abstractmethod
    async def start(self) -> None:
        ...

    @abc.abstractmethod
    def add_http_route(self, path: str, handle) -> None:
        ...

    @abc.abstractmethod
    def add_websocket_route(
        self, path: str, handle: Coro[[Session], None] | None = None
    ) -> None:
        ...

    @abc.abstractmethod
    def add_listener(self, listener: NetworkListener) -> None:
        ...

    @abc.abstractmethod
    def remove_listener(self, listener: NetworkListener) -> None:
        ...


class NetworkListener:
    async def on_start(self) -> None:
        ...

    async def on_connected(self, session: Session) -> None:
        ...

    async def on_disconnected(self, session: Session) -> None:
        ...

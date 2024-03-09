from __future__ import annotations

import abc
from typing import TYPE_CHECKING
from omu.event_emitter import EventEmitter

from omuserver.session import Session

if TYPE_CHECKING:
    from omu.helper import Coro


class Network(abc.ABC):
    @abc.abstractmethod
    async def start(self) -> None: ...

    @abc.abstractmethod
    def add_http_route(self, path: str, handle) -> None: ...

    @abc.abstractmethod
    def add_websocket_route(
        self, path: str, handle: Coro[[Session], None] | None = None
    ) -> None: ...

    @property
    @abc.abstractmethod
    def listeners(self) -> NetworkListeners: ...


class NetworkListeners:
    def __init__(self) -> None:
        self.start = EventEmitter()
        self.connected = EventEmitter[Session]()
        self.disconnected = EventEmitter[Session]()

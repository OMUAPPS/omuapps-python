from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Callable, Coroutine, Literal

from omu.event_emitter import EventEmitter
from omu.network.packet.packet import PacketData

if TYPE_CHECKING:
    from omu.network import Address
    from omu.network.packet import PacketType


type ConnectionStatus = Literal["connecting", "connected", "disconnected"]


class ConnectionListeners:
    def __init__(self) -> None:
        self.connected = EventEmitter()
        self.disconnected = EventEmitter()
        self.packet = EventEmitter[PacketData]()
        self.status_changed = EventEmitter[ConnectionStatus]()


class Connection(abc.ABC):
    @property
    @abc.abstractmethod
    def address(self) -> Address: ...

    @property
    @abc.abstractmethod
    def connected(self) -> bool: ...

    @abc.abstractmethod
    async def connect(
        self, *, token: str | None = None, reconnect: bool = True
    ) -> None: ...

    @abc.abstractmethod
    async def disconnect(self) -> None: ...

    @abc.abstractmethod
    async def send[T](self, event: PacketType[T], data: T) -> None: ...

    @property
    @abc.abstractmethod
    def listeners(self) -> ConnectionListeners: ...

    @abc.abstractmethod
    def add_task(self, task: Callable[[], Coroutine[None, None, None]]) -> None: ...

    @abc.abstractmethod
    def remove_task(self, task: Callable[[], Coroutine[None, None, None]]) -> None: ...

from __future__ import annotations

import abc
from typing import TYPE_CHECKING
from omu.event_emitter import EventEmitter
from omu.network.packet import PacketData, PacketType

if TYPE_CHECKING:
    from omu import App

    from omuserver.security import Permission


class Session(abc.ABC):
    @property
    @abc.abstractmethod
    def app(self) -> App: ...

    @property
    @abc.abstractmethod
    def closed(self) -> bool: ...

    @property
    @abc.abstractmethod
    def permissions(self) -> Permission: ...

    @abc.abstractmethod
    async def disconnect(self) -> None: ...

    @abc.abstractmethod
    async def listen(self) -> None: ...

    @abc.abstractmethod
    async def send[T](self, type: PacketType[T], data: T) -> None: ...

    @property
    @abc.abstractmethod
    def listeners(self) -> SessionListeners: ...


class SessionListeners:
    def __init__(self) -> None:
        self.packet = EventEmitter[Session, PacketData]()
        self.disconnected = EventEmitter[Session]()

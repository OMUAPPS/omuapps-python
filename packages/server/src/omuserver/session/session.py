from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omu import App
    from omu.event import EventData, EventType

    from omuserver.security import Permission


class Session(abc.ABC):
    @property
    @abc.abstractmethod
    def app(self) -> App:
        ...

    @property
    @abc.abstractmethod
    def closed(self) -> bool:
        ...

    @property
    @abc.abstractmethod
    def permissions(self) -> Permission:
        ...

    @abc.abstractmethod
    async def disconnect(self) -> None:
        ...

    @abc.abstractmethod
    async def listen(self) -> None:
        ...

    @abc.abstractmethod
    async def send[T](self, type: EventType[T], data: T) -> None:
        ...

    @abc.abstractmethod
    def add_listener(self, listener: SessionListener) -> None:
        ...

    @abc.abstractmethod
    def remove_listener(self, listener: SessionListener) -> None:
        ...


class SessionListener:
    async def on_event(self, session: Session, event: EventData) -> None:
        ...

    async def on_disconnected(self, session: Session) -> None:
        ...

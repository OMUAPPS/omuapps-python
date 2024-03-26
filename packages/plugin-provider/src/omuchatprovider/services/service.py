from __future__ import annotations

import abc
import typing

from omuchat import Channel, Client, Provider, Room

type ChatSupplier = typing.Callable[[], typing.Coroutine[None, None, ChatService]]


class ProviderService(abc.ABC):
    @abc.abstractmethod
    def __init__(self, client: Client): ...

    @property
    @abc.abstractmethod
    def info(self) -> Provider: ...

    @abc.abstractmethod
    async def fetch_rooms(
        self, channel: Channel
    ) -> typing.Mapping[Room, ChatSupplier]: ...

    @abc.abstractmethod
    async def is_online(self, room: Room) -> bool: ...


class ChatService(abc.ABC):
    @property
    @abc.abstractmethod
    def room(self) -> Room: ...

    @property
    @abc.abstractmethod
    def closed(self) -> bool: ...

    @abc.abstractmethod
    async def start(self): ...

    @abc.abstractmethod
    async def stop(self): ...

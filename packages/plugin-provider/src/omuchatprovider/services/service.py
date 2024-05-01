from __future__ import annotations

import abc
from dataclasses import dataclass

from omu.helper import Coro
from omuchat import Channel, Client, Provider, Room

type ChatServiceFactory = Coro[[], ChatService]


@dataclass(frozen=True)
class FetchedRoom:
    room: Room
    create: ChatServiceFactory


class ProviderService(abc.ABC):
    @abc.abstractmethod
    def __init__(self, client: Client): ...

    @property
    @abc.abstractmethod
    def provider(self) -> Provider: ...

    @abc.abstractmethod
    async def fetch_rooms(self, channel: Channel) -> list[FetchedRoom]: ...

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

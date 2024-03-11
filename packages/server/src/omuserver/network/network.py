from __future__ import annotations

import abc
from omu.event_emitter import EventEmitter
from omu.network.packet.packet import PacketType
from omuserver.session import Session


class Network(abc.ABC):
    @abc.abstractmethod
    async def start(self) -> None: ...

    @abc.abstractmethod
    def add_http_route(self, path: str, handle) -> None: ...

    @abc.abstractmethod
    def register_packet(self, *packet_types: PacketType) -> None: ...

    @abc.abstractmethod
    async def process_session(self, session: Session) -> None: ...

    @property
    @abc.abstractmethod
    def listeners(self) -> NetworkListeners: ...


class NetworkListeners:
    def __init__(self) -> None:
        self.start = EventEmitter()
        self.connected = EventEmitter[Session]()
        self.disconnected = EventEmitter[Session]()

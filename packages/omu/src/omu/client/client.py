from __future__ import annotations

import abc
import asyncio
from typing import TYPE_CHECKING

from omu.event_emitter import EventEmitter

if TYPE_CHECKING:
    from omu.app import App
    from omu.extension import ExtensionManager
    from omu.extension.dashboard import DashboardExtension
    from omu.extension.endpoint import EndpointExtension
    from omu.extension.message import MessageExtension
    from omu.extension.permission import PermissionExtension
    from omu.extension.registry import RegistryExtension
    from omu.extension.server import ServerExtension
    from omu.extension.table import TableExtension
    from omu.network import Network
    from omu.network.packet import PacketType


class ClientListeners:
    def __init__(self) -> None:
        self.initialized = EventEmitter[[]]()
        self.started = EventEmitter[[]]()
        self.stopped = EventEmitter[[]]()
        self.ready = EventEmitter[[]]()


class Client(abc.ABC):
    @property
    @abc.abstractmethod
    def app(self) -> App: ...

    @property
    @abc.abstractmethod
    def loop(self) -> asyncio.AbstractEventLoop: ...

    @property
    @abc.abstractmethod
    def network(self) -> Network: ...

    @property
    @abc.abstractmethod
    def extensions(self) -> ExtensionManager: ...

    @property
    @abc.abstractmethod
    def endpoints(self) -> EndpointExtension: ...

    @property
    @abc.abstractmethod
    def tables(self) -> TableExtension: ...

    @property
    @abc.abstractmethod
    def registry(self) -> RegistryExtension: ...

    @property
    @abc.abstractmethod
    def message(self) -> MessageExtension: ...

    @property
    @abc.abstractmethod
    def server(self) -> ServerExtension: ...

    @property
    @abc.abstractmethod
    def permissions(self) -> PermissionExtension: ...

    @property
    @abc.abstractmethod
    def dashboard(self) -> DashboardExtension: ...

    @property
    @abc.abstractmethod
    def running(self) -> bool: ...

    @abc.abstractmethod
    def run(self) -> None: ...

    @abc.abstractmethod
    async def start(self) -> None: ...

    @abc.abstractmethod
    async def stop(self) -> None: ...

    @abc.abstractmethod
    async def send[T](self, type: PacketType[T], data: T) -> None: ...

    @property
    @abc.abstractmethod
    def listeners(self) -> ClientListeners: ...

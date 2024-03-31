from __future__ import annotations

import abc
import asyncio
from typing import TYPE_CHECKING

from omu.event_emitter import EventEmitter

if TYPE_CHECKING:
    from omu.network import Address

    from omuserver.config import Config
    from omuserver.directories import Directories
    from omuserver.extension.asset import AssetExtension
    from omuserver.extension.dashboard import DashboardExtension
    from omuserver.extension.endpoint import EndpointExtension
    from omuserver.extension.message import MessageExtension
    from omuserver.extension.permission import PermissionExtension
    from omuserver.extension.plugin import PluginExtension
    from omuserver.extension.registry import RegistryExtension
    from omuserver.extension.table import TableExtension
    from omuserver.network import Network
    from omuserver.network.packet_dispatcher import ServerPacketDispatcher
    from omuserver.security import Security


class ServerListeners:
    def __init__(self) -> None:
        self.start = EventEmitter()
        self.stop = EventEmitter()


class Server(abc.ABC):
    @property
    @abc.abstractmethod
    def config(self) -> Config: ...

    @property
    @abc.abstractmethod
    def loop(self) -> asyncio.AbstractEventLoop: ...

    @property
    @abc.abstractmethod
    def address(self) -> Address: ...

    @property
    @abc.abstractmethod
    def directories(self) -> Directories: ...

    @property
    @abc.abstractmethod
    def security(self) -> Security: ...

    @property
    @abc.abstractmethod
    def network(self) -> Network: ...

    @property
    @abc.abstractmethod
    def packet_dispatcher(self) -> ServerPacketDispatcher: ...

    @property
    @abc.abstractmethod
    def permissions(self) -> PermissionExtension: ...

    @property
    @abc.abstractmethod
    def endpoints(self) -> EndpointExtension: ...

    @property
    @abc.abstractmethod
    def dashboard(self) -> DashboardExtension: ...

    @property
    @abc.abstractmethod
    def tables(self) -> TableExtension: ...

    @property
    @abc.abstractmethod
    def registry(self) -> RegistryExtension: ...

    @property
    @abc.abstractmethod
    def messages(self) -> MessageExtension: ...

    @property
    @abc.abstractmethod
    def plugins(self) -> PluginExtension: ...

    @property
    @abc.abstractmethod
    def assets(self) -> AssetExtension: ...

    @property
    @abc.abstractmethod
    def running(self) -> bool: ...

    @abc.abstractmethod
    def run(self) -> None: ...

    @abc.abstractmethod
    async def start(self) -> None: ...

    @abc.abstractmethod
    async def shutdown(self) -> None: ...

    @property
    @abc.abstractmethod
    def listeners(self) -> ServerListeners: ...

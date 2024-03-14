from __future__ import annotations

import abc
from typing import TYPE_CHECKING

from omu.network.packet import Packet, PacketData
from omu.serializer import Serializable

if TYPE_CHECKING:
    from omu.network.network import Network


class Connection(abc.ABC):
    @abc.abstractmethod
    async def connect(self) -> Network: ...

    @abc.abstractmethod
    async def send(
        self,
        packet: Packet,
        serializer: Serializable[Packet, PacketData],
    ) -> None: ...

    @abc.abstractmethod
    async def receive(
        self,
        serializer: Serializable[Packet, PacketData],
    ) -> Packet: ...

    @abc.abstractmethod
    async def close(self) -> None: ...

    @property
    @abc.abstractmethod
    def closed(self) -> bool: ...

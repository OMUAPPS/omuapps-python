from __future__ import annotations
import asyncio
from typing import List


from omu.network.connection import Connection, PacketMapper
from omu.network.packet.packet import Packet


class PluginConnection(Connection):
    def __init__(self) -> None:
        self._connected = False
        self._to_client_queue: List[Packet] = []
        self._to_server_queue: List[Packet] = []
        self._to_client_event = asyncio.Event()
        self._to_server_event = asyncio.Event()

    async def connect(self) -> None:
        self._connected = True

    async def receive(self, packet_mapper: PacketMapper) -> Packet:
        while not self._to_client_queue:
            await self._to_client_event.wait()
            self._to_client_event.clear()
        return self._to_client_queue.pop(0)

    def add_receive(self, packet: Packet) -> None:
        self._to_client_queue.append(packet)
        self._to_client_event.set()

    async def send(self, packet: Packet, packet_mapper: PacketMapper) -> None:
        self._to_server_queue.append(packet)
        self._to_server_event.set()

    async def dequeue_to_server_packet(self) -> Packet:
        while not self._to_server_queue:
            await self._to_server_event.wait()
            self._to_server_event.clear()
        return self._to_server_queue.pop(0)

    @property
    def closed(self) -> bool:
        return not self._connected

    async def close(self) -> None:
        self._connected = False

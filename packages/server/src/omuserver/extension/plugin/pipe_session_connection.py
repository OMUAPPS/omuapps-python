from __future__ import annotations
import asyncio
from multiprocessing.connection import PipeConnection
import threading
from omu.network.packet import Packet, PacketData
from omu.network.connection import PacketMapper

from omuserver.session import SessionConnection


class PipeSessionConnection(SessionConnection):
    def __init__(self, parent_pipe: PipeConnection) -> None:
        self.parent_pipe = parent_pipe
        self.queue: asyncio.Queue[PacketData] = asyncio.Queue()
        self._closed = False
        threading.Thread(target=self._read_thread, daemon=True).start()

    @property
    def closed(self) -> bool:
        return not self._closed

    async def receive(self, packet_mapper: PacketMapper) -> Packet:
        packet = packet_mapper.deserialize(await self.queue.get())
        return packet

    def _read_thread(self) -> None:
        while not self._closed:
            if self.parent_pipe.poll():
                packet = self.parent_pipe.recv()
                self.queue.put_nowait(packet)

    async def close(self) -> None:
        self._closed = True

    async def send(self, packet: Packet, packet_mapper: PacketMapper) -> None:
        if self._closed:
            raise ValueError("Socket is closed")
        self.parent_pipe.send(packet_mapper.serialize(packet))

    def __repr__(self) -> str:
        return f"PipeSessionConnection({self.parent_pipe})"

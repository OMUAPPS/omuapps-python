from __future__ import annotations
import asyncio
from multiprocessing.connection import PipeConnection
import threading


from omu.network.connection import Connection, PacketMapper
from omu.network.packet import Packet, PacketData


class PipePluginConnection(Connection):
    def __init__(self, child_pipe: PipeConnection) -> None:
        self._closed = False
        self.child_pipe = child_pipe
        self.queue: asyncio.Queue[PacketData] = asyncio.Queue()
        threading.Thread(target=self._read_thread, daemon=True).start()

    async def connect(self) -> None:
        self._closed = False

    async def receive(self, packet_mapper: PacketMapper) -> Packet:
        return packet_mapper.deserialize(await self.queue.get())

    async def send(self, packet: Packet, packet_mapper: PacketMapper) -> None:
        self.child_pipe.send(packet_mapper.serialize(packet))

    def _read_thread(self) -> None:
        while not self._closed:
            if self.child_pipe.poll():
                packet = self.child_pipe.recv()
                self.queue.put_nowait(packet)

    @property
    def closed(self) -> bool:
        return self._closed

    async def close(self) -> None:
        self._closed = True

    def __repr__(self) -> str:
        return f"PipePluginConnection({self.child_pipe})"

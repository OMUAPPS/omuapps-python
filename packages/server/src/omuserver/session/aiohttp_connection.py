from __future__ import annotations

import websockets
from fastapi import WebSocket
from loguru import logger
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.network.packet import Packet, PacketData
from omu.network.packet_mapper import PacketMapper

from omuserver.security import Permission

from .session import SessionConnection


class WebsocketsConnection(SessionConnection):
    def __init__(self, ws: WebSocket) -> None:
        self.ws = ws
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def permissions(self) -> Permission:
        return self.permissions

    async def receive(self, packet_mapper: PacketMapper) -> Packet:
        try:
            msg = await self.ws.receive_bytes()
            with ByteReader(msg) as reader:
                event_type = reader.read_string()
                event_data = reader.read_byte_array()
            packet_data = PacketData(event_type, event_data)
            return packet_mapper.deserialize(packet_data)
        except websockets.exceptions.ConnectionClosedError:
            self._closed = True
            raise ConnectionError("Connection closed")

    async def close(self) -> None:
        try:
            await self.ws.close()
        except Exception as e:
            logger.warning(f"Error closing socket: {e}")
            logger.error(e)

    async def send(self, packet: Packet, packet_mapper: PacketMapper) -> None:
        if self.closed:
            raise ValueError("Socket is closed")
        packet_data = packet_mapper.serialize(packet)
        writer = ByteWriter()
        writer.write_string(packet_data.type)
        writer.write_byte_array(packet_data.data)
        await self.ws.send_bytes(writer.finish())

    def __repr__(self) -> str:
        return f"WebsocketsConnection(socket={self.ws})"

from __future__ import annotations

from omu.client import Client
from omu.event_emitter import Unlisten
from omu.extension import Extension, ExtensionType
from omu.helper import AsyncCallback
from omu.identifier import Identifier
from omu.network.packet import PacketType
from omu.serializer import Serializer

from .packets import LogMessage, LogPacket

LOGGER_EXTENSION_TYPE = ExtensionType(
    "logger", lambda client: LoggerExtension(client), lambda: []
)
LOGGER_LOG_PERMISSION_ID = LOGGER_EXTENSION_TYPE / "log"


LOGGER_LOG_PACKET = PacketType[LogPacket].create_serialized(
    identifier=LOGGER_EXTENSION_TYPE,
    name="log",
    serializer=LogPacket,
)
LOGGER_LISTEN_PACKET = PacketType[Identifier].create_json(
    identifier=LOGGER_EXTENSION_TYPE,
    name="listen",
    serializer=Serializer.model(Identifier),
)
LOGGER_SERVER_ID = LOGGER_EXTENSION_TYPE / "server"

"""
Usage:
    client.logger.error("鳥が鳴きません")
    client.logger.warning("鳥を鳴かせ中…")
    client.logger.info("鳥が鳴きました")
    client.logger.debug("誰もが驚く鳥が鳴いた理由")
"""


class LoggerExtension(Extension):
    def __init__(self, client: Client):
        client.network.register_packet(
            LOGGER_LOG_PACKET,
            LOGGER_LISTEN_PACKET,
        )
        client.network.add_packet_handler(LOGGER_LOG_PACKET, self.handle_log)
        self.client = client
        self.listeners: dict[Identifier, set[AsyncCallback[LogMessage]]] = {}
        client.permissions.require(LOGGER_LOG_PERMISSION_ID)

    async def log(self, message: LogMessage) -> None:
        packet = LogPacket(
            id=self.client.app.id,
            message=message,
        )
        await self.client.send(LOGGER_LOG_PACKET, packet)

    async def error(self, message: str) -> None:
        await self.log(LogMessage.error(message))

    async def warning(self, message: str) -> None:
        await self.log(LogMessage.warning(message))

    async def info(self, message: str) -> None:
        await self.log(LogMessage.info(message))

    async def debug(self, message: str) -> None:
        await self.log(LogMessage.debug(message))

    async def listen(
        self, id: Identifier, callback: AsyncCallback[[LogMessage]]
    ) -> Unlisten:
        if id not in self.listeners:

            async def on_ready():
                await self.client.send(LOGGER_LISTEN_PACKET, id)

            self.client.when_ready(on_ready)

            self.listeners[id] = set()
        self.listeners[id].add(callback)

        return lambda: self.listeners[id].remove(callback)

    async def handle_log(self, packet: LogPacket) -> None:
        for callback in self.listeners.get(packet.id, []):
            await callback(packet.message)

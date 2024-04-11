from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, DefaultDict, List

from omu.extension.message.message_extension import (
    MESSAGE_BROADCAST_PACKET,
    MESSAGE_LISTEN_PACKET,
    MessagePacket,
)

if TYPE_CHECKING:
    from omu.identifier import Identifier

    from omuserver import Server
    from omuserver.session import Session


class MessageExtension:
    def __init__(self, server: Server):
        self._server = server
        self.messages: DefaultDict[Identifier, List[Session]] = defaultdict(list)
        server.packet_dispatcher.register(
            MESSAGE_LISTEN_PACKET, MESSAGE_BROADCAST_PACKET
        )
        server.packet_dispatcher.add_packet_handler(
            MESSAGE_LISTEN_PACKET, self.handle_listen
        )
        server.packet_dispatcher.add_packet_handler(
            MESSAGE_BROADCAST_PACKET, self.handle_broadcast
        )

    def has(self, key):
        return key in self.messages

    async def handle_listen(self, session: Session, identifier: Identifier) -> None:
        listeners = self.messages[identifier]
        if session in listeners:
            return

        listeners.append(session)
        session.listeners.disconnected += lambda session: listeners.remove(session)

    async def handle_broadcast(self, session: Session, data: MessagePacket) -> None:
        listeners = self.messages[data.id]
        for listener in listeners:
            await listener.send(MESSAGE_BROADCAST_PACKET, data)

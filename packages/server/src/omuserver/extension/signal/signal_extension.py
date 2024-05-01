from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from omu.extension.signal.signal_extension import (
    SIGNAL_BROADCAST_PACKET,
    SIGNAL_LISTEN_PACKET,
    SignalPacket,
)

if TYPE_CHECKING:
    from omu.identifier import Identifier

    from omuserver import Server
    from omuserver.session import Session


class SignalExtension:
    def __init__(self, server: Server):
        self._server = server
        self.signals: defaultdict[Identifier, list[Session]] = defaultdict(list)
        server.packet_dispatcher.register(SIGNAL_LISTEN_PACKET, SIGNAL_BROADCAST_PACKET)
        server.packet_dispatcher.add_packet_handler(
            SIGNAL_LISTEN_PACKET, self.handle_listen
        )
        server.packet_dispatcher.add_packet_handler(
            SIGNAL_BROADCAST_PACKET, self.handle_broadcast
        )

    def has(self, key):
        return key in self.signals

    async def handle_listen(self, session: Session, identifier: Identifier) -> None:
        listeners = self.signals[identifier]
        if session in listeners:
            return

        listeners.append(session)
        session.listeners.disconnected += lambda session: listeners.remove(session)

    async def handle_broadcast(self, session: Session, data: SignalPacket) -> None:
        listeners = self.signals[data.id]
        for listener in listeners:
            await listener.send(SIGNAL_BROADCAST_PACKET, data)

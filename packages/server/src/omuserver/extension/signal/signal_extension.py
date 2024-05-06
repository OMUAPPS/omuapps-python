from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from omu.extension.signal.packets import SignalRegisterPacket
from omu.extension.signal.signal import SignalPermissions
from omu.extension.signal.signal_extension import (
    SIGNAL_LISTEN_PACKET,
    SIGNAL_NOTIFY_PACKET,
    SIGNAL_REGISTER_PACKET,
    SignalPacket,
)

if TYPE_CHECKING:
    from omu.identifier import Identifier

    from omuserver import Server
    from omuserver.session import Session


@dataclass
class ServerSignal:
    server: Server
    identifier: Identifier
    listeners: list[Session]
    permissions: SignalPermissions

    async def notify(self, body: bytes) -> None:
        packet = SignalPacket(id=self.identifier, body=body)
        for listener in self.listeners:
            await listener.send(SIGNAL_NOTIFY_PACKET, packet)

    def attach_session(self, session: Session) -> None:
        if session in self.listeners:
            raise Exception("Session already attached")
        self.listeners.append(session)
        session.listeners.disconnected += self.detach_session

    def detach_session(self, session: Session) -> None:
        if session not in self.listeners:
            raise Exception("Session not attached")
        self.listeners.remove(session)


class SignalExtension:
    def __init__(self, server: Server):
        self._server = server
        self.signals: dict[Identifier, ServerSignal] = {}
        server.packet_dispatcher.register(
            SIGNAL_REGISTER_PACKET,
            SIGNAL_LISTEN_PACKET,
            SIGNAL_NOTIFY_PACKET,
        )
        server.packet_dispatcher.add_packet_handler(
            SIGNAL_REGISTER_PACKET, self.handle_register
        )
        server.packet_dispatcher.add_packet_handler(
            SIGNAL_LISTEN_PACKET, self.handle_listen
        )
        server.packet_dispatcher.add_packet_handler(
            SIGNAL_NOTIFY_PACKET, self.handle_broadcast
        )

    def get_signal(self, identifier: Identifier) -> ServerSignal:
        if identifier in self.signals:
            return self.signals[identifier]
        signal = ServerSignal(
            server=self._server,
            identifier=identifier,
            listeners=[],
            permissions=SignalPermissions(),
        )
        self.signals[identifier] = signal
        return signal

    async def handle_register(
        self, session: Session, data: SignalRegisterPacket
    ) -> None:
        signal = self.get_signal(data.id)
        signal.permissions = data.permissions

    async def handle_listen(self, session: Session, identifier: Identifier) -> None:
        signal = self.get_signal(identifier)
        signal.attach_session(session)

    async def handle_broadcast(self, session: Session, data: SignalPacket) -> None:
        signal = self.get_signal(data.id)
        await signal.notify(data.body)

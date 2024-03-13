from __future__ import annotations

from typing import Dict

from omu.app import App
from omu.identifier import Identifier
from omu.model import Model
from omu.network.packet import PacketType
from omu.serializer import Serializer


class ConnectPacket(Model):
    def __init__(self, app: App, token: str | None = None):
        self.app = app
        self.token = token

    def to_json(self) -> Dict:
        return {
            "app": self.app.to_json(),
            "token": self.token,
        }

    @classmethod
    def from_json(cls, json: Dict) -> ConnectPacket:
        return cls(
            app=App.from_json(json["app"]),
            token=json["token"],
        )


class DisconnectPacket(Model):
    def __init__(self, reason: str):
        self.reason = reason

    def to_json(self) -> Dict:
        return {"reason": self.reason}

    @classmethod
    def from_json(cls, json: Dict) -> DisconnectPacket:
        return cls(
            reason=json["reason"],
        )


class PACKET_TYPES:
    IDENTIFIER = Identifier("core", "packet")
    Connect = PacketType.create_json(
        IDENTIFIER,
        "connect",
        Serializer.model(ConnectPacket),
    )
    Disconnect = PacketType.create_json(
        IDENTIFIER,
        "disconnect",
        Serializer.model(DisconnectPacket),
    )
    Token = PacketType[str].create_json(
        IDENTIFIER,
        "token",
        Serializer.noop(),
    )
    Ready = PacketType[None].create_json(
        IDENTIFIER,
        "ready",
        Serializer.noop(),
    )

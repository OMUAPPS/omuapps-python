from __future__ import annotations

from typing import Mapping

from omu.app import App
from omu.identifier import Identifier
from omu.model import Model
from omu.serializer import Serializer

from .packet import PacketType


class ConnectPacket(Model):
    def __init__(self, app: App, token: str | None = None):
        self.app = app
        self.token = token

    def to_json(self) -> Mapping:
        return {
            "app": self.app.to_json(),
            "token": self.token,
        }

    @classmethod
    def from_json(cls, json: Mapping) -> ConnectPacket:
        return cls(
            app=App.from_json(json["app"]),
            token=json["token"],
        )


class DisconnectPacket(Model):
    def __init__(self, reason: str):
        self.reason = reason

    def to_json(self) -> Mapping:
        return {"reason": self.reason}

    @classmethod
    def from_json(cls, json: Mapping) -> DisconnectPacket:
        return cls(
            reason=json["reason"],
        )


class PACKET_TYPES:
    IDENTIFIER = Identifier("core", "packet")
    CONNECT = PacketType.create_json(
        IDENTIFIER,
        "connect",
        Serializer.model(ConnectPacket),
    )
    DISCONNECT = PacketType.create_json(
        IDENTIFIER,
        "disconnect",
        Serializer.model(DisconnectPacket),
    )
    TOKEN = PacketType[str].create_json(
        IDENTIFIER,
        "token",
        Serializer.noop(),
    )
    READY = PacketType[None].create_json(
        IDENTIFIER,
        "ready",
        Serializer.noop(),
    )

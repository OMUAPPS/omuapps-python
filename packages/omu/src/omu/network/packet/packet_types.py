from __future__ import annotations

from enum import Enum
from typing import TypedDict

from pydantic import BaseModel

from omu.app import App
from omu.identifier import Identifier
from omu.serializer import Serializer

from .packet import PacketType


class ConnectPacket(BaseModel):
    app: App
    token: str | None = None


class DisconnectType(str, Enum):
    INVALID_TOKEN = "invalid_token"
    INVALID_ORIGIN = "invalid_origin"
    INVALID_VERSION = "invalid_version"
    INVALID_PACKET_TYPE = "invalid_packet_type"
    INVALID_PACKET_DATA = "invalid_packet_data"
    INVALID_PACKET = "invalid_packet"
    ANOTHER_CONNECTION = "another_connection"
    PERMISSION_DENIED = "permission_denied"
    SHUTDOWN = "shutdown"
    CLOSE = "close"


class DisconnectPacketData(TypedDict):
    type: str
    message: str | None


class DisconnectPacket(BaseModel):
    type: DisconnectType
    message: str | None = None


IDENTIFIER = Identifier.from_key("core:packet")


class PACKET_TYPES:
    CONNECT = PacketType.create_json(
        IDENTIFIER,
        "connect",
        Serializer.pydantic(ConnectPacket),
    )
    DISCONNECT = PacketType.create_json(
        IDENTIFIER,
        "disconnect",
        Serializer.pydantic(DisconnectPacket),
    )
    TOKEN = PacketType[str].create_json(
        IDENTIFIER,
        "token",
    )
    READY = PacketType[None].create_json(
        IDENTIFIER,
        "ready",
    )

from typing import Dict

from omu.event import JsonEventType
from omu.extension.server import App
from omu.extension.table import Model
from omu.serializer import Serializer


class ConnectEvent(Model):
    def __init__(self, app: App, token: str | None = None):
        self.app = app
        self.token = token

    def to_json(self) -> Dict:
        return {
            "app": self.app.to_json(),
            "token": self.token,
        }

    @classmethod
    def from_json(cls, json: Dict) -> "ConnectEvent":
        return cls(
            app=App.from_json(json["app"]),
            token=json["token"],
        )


class DisconnectEvent(Model):
    def __init__(self, reason: str):
        self.reason = reason

    def to_json(self) -> Dict:
        return {"reason": self.reason}

    @classmethod
    def from_json(cls, json: Dict) -> "DisconnectEvent":
        return cls(
            reason=json["reason"],
        )


class EVENTS:
    Connect = JsonEventType(
        "",
        "connect",
        Serializer.model(ConnectEvent),
    )
    Disconnect = JsonEventType(
        "",
        "disconnect",
        Serializer.model(DisconnectEvent),
    )
    Token = JsonEventType[str](
        "",
        "token",
        Serializer.noop(),
    )
    Ready = JsonEventType[None](
        "",
        "ready",
        Serializer.noop(),
    )

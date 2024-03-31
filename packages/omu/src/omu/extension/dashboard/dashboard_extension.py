from __future__ import annotations

from typing import Any, List, TypedDict

from omu.app import App
from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
from omu.extension.permission.permission import PermissionType
from omu.identifier import Identifier
from omu.model import Model
from omu.network.packet.packet import PacketType
from omu.serializer import Serializer

DashboardExtensionType = ExtensionType(
    "Dashboard",
    lambda client: DashboardExtension(client),
    lambda: [],
)


class DashboardExtension(Extension):
    def __init__(self, client: Client):
        self.client = client

        self.client.network.register_packet(
            DashboardRequestPermissionPacket,
        )


class DashboardSetResponse(TypedDict):
    ok: bool


DashboardSetEndpoint = EndpointType[Identifier, DashboardSetResponse].create_serialized(
    DashboardExtensionType,
    "set",
    request_serializer=Serializer.model(Identifier).pipe(Serializer.json()),
    response_serializer=Serializer.json(),
)


class PermissionRequest(Model):
    request_id: int
    app: App
    permissions: List[PermissionType]

    @classmethod
    def from_json(cls, json: dict[str, Any]) -> PermissionRequest:
        return cls(
            app=App.from_json(json["app"]),
            permissions=[PermissionType.from_json(p) for p in json["permissions"]],
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "app": self.app.to_json(),
            "permissions": [p.to_json() for p in self.permissions],
        }


DashboardRequestPermissionPacket = PacketType.create_json(
    DashboardExtensionType,
    "request_permission",
    Serializer.model(PermissionRequest),
)

DashboardAcceptPermissionPacket = PacketType[int].create_json(
    DashboardExtensionType,
    "accept_permission",
)

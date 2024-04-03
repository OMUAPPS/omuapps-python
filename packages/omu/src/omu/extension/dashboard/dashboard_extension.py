from __future__ import annotations

from typing import TypedDict

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
from omu.identifier import Identifier
from omu.network.packet import PacketType
from omu.serializer import Serializer

from .dashboard import PermissionRequest

DASHBOARD_EXTENSION_TYPE = ExtensionType(
    "dashboard",
    lambda client: DashboardExtension(client),
    lambda: [],
)


class DashboardExtension(Extension):
    def __init__(self, client: Client):
        self.client = client

        self.client.network.register_packet(
            DASHBOARD_PERMISSION_REQUEST_PACKET,
            DASHBOARD_PERMISSION_ACCEPT_PACKET,
            DASHBOARD_PERMISSION_DENY_PACKET,
        )


class DashboardSetResponse(TypedDict):
    success: bool


DASHBOARD_SET_ENDPOINT = EndpointType[
    Identifier, DashboardSetResponse
].create_serialized(
    DASHBOARD_EXTENSION_TYPE,
    "set",
    request_serializer=Serializer.model(Identifier).pipe(Serializer.json()),
    response_serializer=Serializer.json(),
)
DASHBOARD_PERMISSION_REQUEST_PACKET = PacketType.create_json(
    DASHBOARD_EXTENSION_TYPE,
    "permission_request",
    Serializer.model(PermissionRequest),
)
DASHBOARD_PERMISSION_ACCEPT_PACKET = PacketType[int].create_json(
    DASHBOARD_EXTENSION_TYPE,
    "permission_accept",
)
DASHBOARD_PERMISSION_DENY_PACKET = PacketType[int].create_json(
    DASHBOARD_EXTENSION_TYPE,
    "permission_deny",
)

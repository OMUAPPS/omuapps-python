from typing import Dict, List

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint.endpoint import EndpointType
from omu.identifier import Identifier
from omu.network.packet.packet import PacketType
from omu.serializer import Serializer

from .permission import PermissionType

PERMISSION_EXTENSION_TYPE = ExtensionType(
    "permission",
    lambda client: PermissionExtension(client),
    lambda: [],
)


class PermissionExtension(Extension):
    def __init__(self, client: Client):
        self.client = client
        self.permissions: List[PermissionType] = []
        self.registered_permissions: Dict[Identifier, PermissionType] = {}
        self.required_permissions: Dict[Identifier, PermissionType] = {}
        client.network.register_packet(
            PERMISSION_REGISTER_PACKET,
            PERMISSION_GRANT_PACKET,
        )
        client.network.add_packet_handler(
            PERMISSION_GRANT_PACKET,
            self.handle_grant,
        )
        client.network.listeners.connected += self.on_connected

    def register(self, permission: PermissionType):
        base_identifier = self.client.app.identifier
        if not permission.identifier.is_subpath_of(base_identifier):
            raise ValueError(
                f"Permission identifier {permission.identifier} is not a subpath of app identifier {base_identifier}"
            )
        self.registered_permissions[permission.identifier] = permission

    def require(self, permission: PermissionType):
        self.required_permissions[permission.identifier] = permission

    def has(self, permission_identifier: Identifier):
        return permission_identifier in self.permissions

    async def on_connected(self):
        await self.client.send(
            PERMISSION_REGISTER_PACKET,
            [*self.registered_permissions.values()],
        )
        await self.client.endpoints.call(
            PERMISSION_REQUEST_ENDPOINT,
            [*self.required_permissions.keys()],
        )

    async def handle_grant(self, permissions: List[PermissionType]):
        self.permissions = permissions


PERMISSION_REGISTER_PACKET = PacketType.create_json(
    PERMISSION_EXTENSION_TYPE,
    "register",
    Serializer.model(PermissionType).array(),
)
PERMISSION_REQUEST_ENDPOINT = EndpointType[List[Identifier], None].create_json(
    PERMISSION_EXTENSION_TYPE,
    "request",
    request_serializer=Serializer.model(Identifier).array(),
)
PERMISSION_GRANT_PACKET = PacketType.create_json(
    PERMISSION_EXTENSION_TYPE,
    "grant",
    Serializer.model(PermissionType).array(),
)

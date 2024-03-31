from typing import Dict, List

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint.endpoint import EndpointType
from omu.identifier import Identifier
from omu.network.packet.packet import PacketType
from omu.serializer import Serializer

from .permission import PermissionType

PermissionExtensionType = ExtensionType(
    "permission",
    lambda client: PermissionExtension(client),
    lambda: [],
)


class PermissionExtension(Extension):
    def __init__(self, client: Client):
        self.client = client
        self.permissions: List[Identifier] = []
        self.registered_permissions: Dict[Identifier, PermissionType] = {}
        self.require_permissions: Dict[Identifier, PermissionType] = {}
        self.client.network.register_packet(
            PermissionRegisterPacket,
            PermissionGrantPacket,
        )
        self.client.network.add_packet_handler(
            PermissionGrantPacket,
            self.handle_grant,
        )
        self.client.network.listeners.connected += self.on_connected

    def register(self, permission: PermissionType):
        base_identifier = self.client.app.identifier
        if not permission.identifier.is_subpath_of(base_identifier):
            raise ValueError(
                f"Permission identifier {permission.identifier} is not a subpath of app identifier {base_identifier}"
            )
        self.registered_permissions[permission.identifier] = permission

    def request(self, permission: PermissionType):
        self.require_permissions[permission.identifier] = permission

    def has(self, permission: PermissionType):
        return permission.identifier in self.permissions

    async def on_connected(self):
        await self.client.endpoints.call(
            PermissionRequestEndpoint, [*self.require_permissions.keys()]
        )

    async def handle_grant(self, permissions: List[Identifier]):
        self.permissions = permissions


PermissionRegisterPacket = PacketType.create_serialized(
    PermissionExtensionType,
    "register",
    Serializer.model(PermissionType).array().pipe(Serializer.json()),
)

PermissionRequestEndpoint = EndpointType[List[Identifier], None].create_serialized(
    PermissionExtensionType,
    "request",
    request_serializer=Serializer.model(Identifier).array().pipe(Serializer.json()),
    response_serializer=Serializer.json(),
)

PermissionGrantPacket = PacketType.create_json(
    PermissionExtensionType,
    "grant",
    Serializer.model(Identifier).array(),
)

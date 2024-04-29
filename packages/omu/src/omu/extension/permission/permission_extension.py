from typing import Dict, List, Set

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
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
        self.required_permission_ids: Set[Identifier] = set()
        client.network.register_packet(
            PERMISSION_REGISTER_PACKET,
            PERMISSION_REQUIRE_PACKET,
            PERMISSION_GRANT_PACKET,
        )
        client.network.add_packet_handler(
            PERMISSION_GRANT_PACKET,
            self.handle_grant,
        )
        client.network.listeners.connected += self.on_connected
        client.network.add_task(self.on_network_task)

    def register(self, *permission_types: PermissionType):
        for permission in permission_types:
            if permission.id in self.registered_permissions:
                raise ValueError(f"Permission {permission.id} already registered")
            base_identifier = self.client.app.identifier
            if not permission.id.is_subpart_of(base_identifier):
                raise ValueError(
                    f"Permission identifier {permission.id} is not a subpart of app identifier {base_identifier}"
                )
            self.registered_permissions[permission.id] = permission

    def require(self, permission_id: Identifier):
        self.required_permission_ids.add(permission_id)

    async def request(self, *permissions_ids: Identifier):
        self.required_permission_ids = {
            *self.required_permission_ids,
            *permissions_ids,
        }
        await self.client.endpoints.call(
            PERMISSION_REQUEST_ENDPOINT, [*self.required_permission_ids]
        )

    def has(self, permission_identifier: Identifier):
        return permission_identifier in self.permissions

    async def on_connected(self):
        await self.client.send(
            PERMISSION_REGISTER_PACKET,
            [*self.registered_permissions.values()],
        )

    async def on_network_task(self):
        if len(self.required_permission_ids) > 0:
            await self.client.send(
                PERMISSION_REQUIRE_PACKET,
                [*self.required_permission_ids],
            )

    async def handle_grant(self, permissions: List[PermissionType]):
        self.permissions = permissions


PERMISSION_REGISTER_PACKET = PacketType[List[PermissionType]].create_json(
    PERMISSION_EXTENSION_TYPE,
    "register",
    Serializer.model(PermissionType).to_array(),
)
PERMISSION_REQUIRE_PACKET = PacketType[List[Identifier]].create_json(
    PERMISSION_EXTENSION_TYPE,
    "require",
    serializer=Serializer.model(Identifier).to_array(),
)
PERMISSION_REQUEST_ENDPOINT = EndpointType[List[Identifier], None].create_json(
    PERMISSION_EXTENSION_TYPE,
    "request",
    request_serializer=Serializer.model(Identifier).to_array(),
)
PERMISSION_GRANT_PACKET = PacketType.create_json(
    PERMISSION_EXTENSION_TYPE,
    "grant",
    Serializer.model(PermissionType).to_array(),
)

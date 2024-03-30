from typing import Dict

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.identifier import Identifier
from omu.network.packet.packet import PacketType
from omu.serializer import Serializer

from .permission import PermissionType

PermissionExtensionType = ExtensionType(
    "registry",
    lambda client: PermissionExtension(client),
    lambda: [],
)


class PermissionExtension(Extension):
    def __init__(self, client: Client):
        self.client = client
        self.registered_permissions: Dict[Identifier, PermissionType] = {}
        self.require_permissions: Dict[Identifier, PermissionType] = {}
        self.client.network.register_packet(
            PermissionRegisterPacket, PermissionRequestPacket
        )

    def register(self, permission: PermissionType):
        base_identifier = self.client.app.identifier
        if not permission.identifier.is_subpath_of(base_identifier):
            raise ValueError(
                f"Permission identifier {permission.identifier} is not a subpath of app identifier {base_identifier}"
            )
        self.registered_permissions[permission.identifier] = permission

    def request(self, permission: PermissionType):
        self.require_permissions[permission.identifier] = permission


PermissionRegisterPacket = PacketType.create_serialized(
    PermissionExtensionType,
    "register",
    Serializer.model(PermissionType).array().pipe(Serializer.json()),
)

PermissionRequestPacket = PacketType.create_serialized(
    PermissionExtensionType,
    "request",
    Serializer.noop().array().pipe(Serializer.json()),
)

PermissionGrantPacket = PacketType.create_serialized(
    PermissionExtensionType,
    "grant",
    Serializer.noop().array().pipe(Serializer.json()),
)

PermissionDenyPacket = PacketType.create_serialized(
    PermissionExtensionType,
    "deny",
    Serializer.noop().array().pipe(Serializer.json()),
)

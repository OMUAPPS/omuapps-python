from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

from omu.extension.dashboard.dashboard import PermissionRequest
from omu.extension.permission.permission import PermissionType
from omu.extension.permission.permission_extension import (
    PERMISSION_GRANT_PACKET,
    PERMISSION_REGISTER_PACKET,
    PERMISSION_REQUEST_ENDPOINT,
)
from omu.identifier import Identifier

from omuserver.session import Session

if TYPE_CHECKING:
    from omuserver.server import Server


class PermissionExtension:
    def __init__(self, server: Server) -> None:
        self.server = server
        self.request_id = 0
        self.permission_registry: Dict[Identifier, PermissionType] = {}
        self.session_permissions: Dict[Session, List[PermissionType]] = {}
        server.packet_dispatcher.register(
            PERMISSION_REGISTER_PACKET,
            PERMISSION_GRANT_PACKET,
        )
        server.packet_dispatcher.add_packet_handler(
            PERMISSION_REGISTER_PACKET,
            self.handle_register,
        )
        server.endpoints.bind_endpoint(
            PERMISSION_REQUEST_ENDPOINT,
            self.handle_request,
        )

    def register(self, permission: PermissionType) -> None:
        if permission.identifier in self.permission_registry:
            raise ValueError(f"Permission {permission.identifier} already registered")
        self.permission_registry[permission.identifier] = permission

    async def handle_register(
        self, session: Session, permissions: List[PermissionType]
    ) -> None:
        for permission in permissions:
            self.permission_registry[permission.identifier] = permission

    async def handle_request(
        self, session: Session, permission_identifiers: List[Identifier]
    ):
        self.request_id += 1
        permissions: List[PermissionType] = []
        for identifier in permission_identifiers:
            permission = self.permission_registry.get(identifier)
            if permission is not None:
                permissions.append(permission)

        accepted = await self.server.dashboard.request_permissions(
            PermissionRequest(self.request_id, session.app, permissions)
        )
        if accepted:
            self.session_permissions[session] = permissions
            await session.send(PERMISSION_GRANT_PACKET, permissions)
        else:
            await session.disconnect()

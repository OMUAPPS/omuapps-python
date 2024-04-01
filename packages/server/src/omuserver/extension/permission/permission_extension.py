from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

from omu.extension.dashboard.dashboard import PermissionRequest
from omu.extension.permission.permission import PermissionType
from omu.extension.permission.permission_extension import (
    PERMISSION_GRANTED_PACKET,
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
        self.permissions: Dict[Identifier, PermissionType] = {}
        server.packet_dispatcher.register(
            PERMISSION_REGISTER_PACKET,
            PERMISSION_GRANTED_PACKET,
        )
        server.packet_dispatcher.add_packet_handler(
            PERMISSION_REGISTER_PACKET,
            self.handle_register,
        )
        server.endpoints.bind_endpoint(
            PERMISSION_REQUEST_ENDPOINT,
            self.handle_request,
        )

    async def handle_register(
        self, session: Session, permissions: List[PermissionType]
    ) -> None:
        for permission in permissions:
            self.permissions[permission.identifier] = permission

    async def handle_request(
        self, session: Session, permission_identifiers: List[Identifier]
    ):
        self.request_id += 1
        permissions = []
        for identifier in permission_identifiers:
            permission = self.permissions.get(identifier)
            if permission is not None:
                permissions.append(permission)
        await self.server.dashboard.request_permissions(
            PermissionRequest(self.request_id, session.app, permissions)
        )

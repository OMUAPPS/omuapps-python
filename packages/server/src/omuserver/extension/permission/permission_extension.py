from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Dict, List

from omu.extension.permission import PermissionType
from omu.extension.permission.permission_extension import (
    PERMISSION_GRANT_PACKET,
    PERMISSION_REGISTER_PACKET,
    PERMISSION_REQUEST_ENDPOINT,
)
from omu.identifier import Identifier
from omu.network.packet.packet_types import DisconnectType

from omuserver.session import Session
from omuserver.session.session import SessionTask

if TYPE_CHECKING:
    from omuserver.server import Server


class PermissionExtension:
    def __init__(self, server: Server) -> None:
        self.server = server
        self.request_id = 0
        self.permission_registry: Dict[Identifier, PermissionType] = {}
        self.session_permissions: Dict[str, Dict[Identifier, PermissionType]] = {}
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
            if not permission.identifier.is_subpart_of(session.app.identifier):
                raise ValueError(
                    f"Permission identifier {permission.identifier} "
                    f"is not a subpart of app identifier {session.app.identifier}"
                )
            self.permission_registry[permission.identifier] = permission

    async def handle_request(
        self, session: Session, permission_identifiers: List[Identifier]
    ):
        task_future = asyncio.Future[None]()
        session.add_task(
            SessionTask(task_future, f"handle_request({permission_identifiers})")
        )

        request_id = self._get_next_request_id()
        permissions: List[PermissionType] = []
        for identifier in permission_identifiers:
            permission = self.permission_registry.get(identifier)
            if permission is not None:
                permissions.append(permission)

        # accepted = await self.server.dashboard.request_permissions(
        #     PermissionRequest(request_id, session.app, permissions)
        # )
        accepted = True
        if accepted:
            self.session_permissions[session.token] = {
                p.identifier: p for p in permissions
            }
            if not session.closed:
                await session.send(PERMISSION_GRANT_PACKET, permissions)
            task_future.set_result(None)
        else:
            await session.disconnect(
                DisconnectType.PERMISSION_DENIED,
                f"Permission request denied (id={request_id})",
            )

    def _get_next_request_id(self) -> str:
        self.request_id += 1
        return f"{self.request_id}-{time.time_ns()}"

    def has_permission(self, session: Session, permission_id: Identifier) -> bool:
        return permission_id in self.session_permissions.get(session.token, {})

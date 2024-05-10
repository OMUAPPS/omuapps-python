from __future__ import annotations

import json
import sqlite3
import time

from omu.extension.dashboard.packets import PermissionRequestPacket
from omu.extension.permission import PermissionType
from omu.extension.permission.permission_extension import (
    PERMISSION_GRANT_PACKET,
    PERMISSION_REGISTER_PACKET,
    PERMISSION_REQUEST_ENDPOINT,
    PERMISSION_REQUIRE_PACKET,
)
from omu.identifier import Identifier
from omu.network.packet.packet_types import DisconnectType

from omuserver.server import Server
from omuserver.session import Session


class PermissionExtension:
    def __init__(self, server: Server) -> None:
        server.packet_dispatcher.register(
            PERMISSION_REGISTER_PACKET,
            PERMISSION_REQUIRE_PACKET,
            PERMISSION_GRANT_PACKET,
        )
        server.packet_dispatcher.add_packet_handler(
            PERMISSION_REGISTER_PACKET,
            self.handle_register,
        )
        server.packet_dispatcher.add_packet_handler(
            PERMISSION_REQUIRE_PACKET,
            self.handle_require,
        )
        server.endpoints.bind_endpoint(
            PERMISSION_REQUEST_ENDPOINT,
            self.handle_request,
        )
        self.server = server
        self.request_id = 0
        self.permission_registry: dict[Identifier, PermissionType] = {}
        self.session_permissions: dict[str, list[Identifier]] = {}
        permission_dir = server.directories.get("permissions")
        permission_dir.mkdir(parents=True, exist_ok=True)
        self.permission_db = sqlite3.connect(permission_dir / "permissions.db")
        self.permission_db.execute(
            """
            CREATE TABLE IF NOT EXISTS permissions (
                id TEXT PRIMARY KEY,
                value BLOB
            )
            """
        )
        self.permission_db.commit()
        self.load_permissions()

    def register(self, *permission_types: PermissionType) -> None:
        for permission in permission_types:
            if permission.id in self.permission_registry:
                raise ValueError(f"Permission {permission.id} already registered")
            self.permission_registry[permission.id] = permission

    async def handle_register(
        self, session: Session, permissions: list[PermissionType]
    ) -> None:
        for permission in permissions:
            if not permission.id.is_subpath_of(session.app.id):
                msg = (
                    f"Permission identifier {permission.id} "
                    f"is not a subpart of app identifier {session.app.id}"
                )
                raise ValueError(msg)
            self.permission_registry[permission.id] = permission

    def load_permissions(self) -> None:
        cursor = self.permission_db.cursor()
        cursor.execute("SELECT id, value FROM permissions")
        for row in cursor:
            token = row[0]
            permissions = json.loads(row[1])
            self.session_permissions[token] = [
                Identifier.from_key(key) for key in permissions
            ]

    def store_permissions(self) -> None:
        cursor = self.permission_db.cursor()
        for token, permissions in self.session_permissions.items():
            permission_keys = [permission.key() for permission in permissions]
            permissions = json.dumps(permission_keys)
            cursor.execute(
                "INSERT OR REPLACE INTO permissions VALUES (?, ?)",
                (token, permissions),
            )
        self.permission_db.commit()

    def set_permissions(self, token: str, permissions: list[Identifier]) -> None:
        self.session_permissions[token] = permissions
        self.store_permissions()

    async def handle_require(
        self, session: Session, permission_identifiers: list[Identifier]
    ):
        if session.ready:
            raise ValueError("Session is already ready")
        if session.is_plugin:
            return
        if set(permission_identifiers) == set(
            self.session_permissions.get(session.token, {})
        ):
            return

        ready_task = await session.create_ready_task(
            f"handle_request({permission_identifiers})"
        )

        request_id = self._get_next_request_id()
        permissions: list[PermissionType] = []
        for permission_id in permission_identifiers:
            permission = self.permission_registry.get(permission_id)
            if permission is None:
                raise ValueError(f"Permission {permission_id} not registered")
            permissions.append(permission)
        if session.is_plugin or session.is_dashboard:
            accepted = True
        else:
            accepted = await self.server.dashboard.request_permissions(
                PermissionRequestPacket(request_id, session.app, permissions)
            )
        if accepted:
            self.set_permissions(session.token, [p.id for p in permissions])
            if not session.closed:
                await session.send(PERMISSION_GRANT_PACKET, permissions)
            ready_task.set()
        else:
            await session.disconnect(
                DisconnectType.PERMISSION_DENIED,
                f"Permission request denied (id={request_id})",
            )

    async def handle_request(
        self, session: Session, permission_identifiers: list[Identifier]
    ):
        request_id = self._get_next_request_id()
        permissions: list[PermissionType] = []
        for identifier in permission_identifiers:
            permission = self.permission_registry.get(identifier)
            if permission is not None:
                permissions.append(permission)

        accepted = await self.server.dashboard.request_permissions(
            PermissionRequestPacket(request_id, session.app, permissions)
        )
        if accepted:
            self.set_permissions(session.token, [p.id for p in permissions])
            if not session.closed:
                await session.send(PERMISSION_GRANT_PACKET, permissions)
        else:
            await session.disconnect(
                DisconnectType.PERMISSION_DENIED,
                f"Permission request denied (id={request_id})",
            )

    def _get_next_request_id(self) -> str:
        self.request_id += 1
        return f"{self.request_id}-{time.time_ns()}"

    def has_permission(self, session: Session, permission_id: Identifier) -> bool:
        if session.is_plugin:
            return True
        return permission_id in self.session_permissions.get(session.token, [])

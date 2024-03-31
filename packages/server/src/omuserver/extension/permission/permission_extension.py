from __future__ import annotations

from typing import TYPE_CHECKING, List

from omu.extension.permission.permission_extension import (
    PermissionRequestEndpoint,
)
from omu.identifier import Identifier

from omuserver.session import Session

if TYPE_CHECKING:
    from omuserver.server import Server


class PermissionExtension:
    def __init__(self, server: Server) -> None:
        server.endpoints.bind_endpoint(
            PermissionRequestEndpoint,
            self.handle_request,
        )

    async def handle_request(self, session: Session, permissions: List[Identifier]):
        pass

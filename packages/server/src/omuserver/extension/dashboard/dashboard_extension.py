from asyncio import Future
from typing import Dict

from omu.extension.dashboard.dashboard import PermissionRequest
from omu.extension.dashboard.dashboard_extension import (
    DASHBOARD_PERMISSION_ACCEPT_PACKET,
    DASHBOARD_PERMISSION_DENY_PACKET,
    DASHBOARD_PERMISSION_REQUEST_PACKET,
    DASHBOARD_SET_ENDPOINT,
    DashboardSetResponse,
)
from omu.identifier import Identifier

from omuserver.server import Server
from omuserver.session import Session


class DashboardExtension:
    def __init__(self, server: Server) -> None:
        self.server = server
        self.dashboard_session: Session | None = None
        self.pending_permission_requests: Dict[int, PermissionRequest] = {}
        self.permission_requests: Dict[int, Future[bool]] = {}
        server.packet_dispatcher.register(
            DASHBOARD_PERMISSION_REQUEST_PACKET,
            DASHBOARD_PERMISSION_ACCEPT_PACKET,
            DASHBOARD_PERMISSION_DENY_PACKET,
        )
        server.endpoints.bind_endpoint(
            DASHBOARD_SET_ENDPOINT,
            self.handle_dashboard_set,
        )
        server.packet_dispatcher.add_packet_handler(
            DASHBOARD_PERMISSION_ACCEPT_PACKET,
            self.handle_permission_accept,
        )
        server.packet_dispatcher.add_packet_handler(
            DASHBOARD_PERMISSION_DENY_PACKET,
            self.handle_permission_deny,
        )

    async def handle_dashboard_set(
        self, session: Session, identifier: Identifier
    ) -> DashboardSetResponse:
        if session.token != self.server.config.dashboard_token:
            raise ValueError("Dashboard token does not match")
        self.dashboard_session = session
        session.listeners.disconnected += self._on_dashboard_disconnected
        await self.send_pending_permission_requests()
        return {"success": True}

    async def _on_dashboard_disconnected(self, session: Session) -> None:
        self.dashboard_session = None

    async def send_pending_permission_requests(self) -> None:
        if self.dashboard_session is None:
            raise ValueError("Dashboard session not set")
        for request in self.pending_permission_requests.values():
            await self.dashboard_session.send(
                DASHBOARD_PERMISSION_REQUEST_PACKET,
                request,
            )
        self.pending_permission_requests.clear()

    async def handle_permission_accept(self, session: Session, request_id: int) -> None:
        future = self.permission_requests.pop(request_id)
        future.set_result(True)

    async def handle_permission_deny(self, session: Session, request_id: int) -> None:
        future = self.permission_requests.pop(request_id)
        future.set_result(False)

    async def request_permissions(self, request: PermissionRequest) -> bool:
        if request.request_id in self.permission_requests:
            raise ValueError(
                f"Permission request with id {request.request_id} already exists"
            )
        future = Future[bool]()
        self.permission_requests[request.request_id] = future
        await self.send_dashboard_permission_request(request)
        return await future

    async def send_dashboard_permission_request(
        self, request: PermissionRequest
    ) -> None:
        if self.dashboard_session is None:
            self.pending_permission_requests[request.request_id] = request
        else:
            await self.dashboard_session.send(
                DASHBOARD_PERMISSION_REQUEST_PACKET,
                request,
            )

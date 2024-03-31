from omu.extension.dashboard.dashboard_extension import (
    DashboardSetEndpoint,
    DashboardSetResponse,
)
from omu.identifier import Identifier
from omuserver.server import Server
from omuserver.session import Session


class DashboardExtension:
    def __init__(self, server: Server) -> None:
        self.server = server
        self.dashboard_session: Session | None = None
        server.endpoints.bind_endpoint(
            DashboardSetEndpoint,
            self.handle_dashboard_set,
        )

    async def handle_dashboard_set(
        self, session: Session, identifier: Identifier
    ) -> DashboardSetResponse:
        self.dashboard_session = session
        return {"ok": True}

from __future__ import annotations

from asyncio import Future
from collections import defaultdict

from loguru import logger
from omu.extension.permission import PermissionType
from omu.extension.server.server_extension import (
    APP_TABLE_TYPE,
    REQUIRE_APPS_PACKET_TYPE,
    SERVER_APPS_READ_PERMISSION_ID,
    SERVER_SHUTDOWN_PERMISSION_ID,
    SHUTDOWN_ENDPOINT_TYPE,
    VERSION_REGISTRY_TYPE,
)
from omu.identifier import Identifier

from omuserver import __version__
from omuserver.helper import get_launch_command
from omuserver.server import Server
from omuserver.session import Session


class WaitHandle:
    def __init__(self, ids: list[Identifier]):
        self.future = Future()
        self.ids = ids


SERVER_SHUTDOWN_PERMISSION = PermissionType(
    id=SERVER_SHUTDOWN_PERMISSION_ID,
    metadata={
        "level": "high",
        "name": {
            "en": "Shutdown Server",
            "ja": "サーバーをシャットダウン",
        },
        "note": {
            "en": "Permission to shutdown the server",
            "ja": "サーバーをシャットダウンできる権限",
        },
    },
)
SERVER_APPS_READ_PERMISSION = PermissionType(
    id=SERVER_APPS_READ_PERMISSION_ID,
    metadata={
        "level": "low",
        "name": {
            "en": "Get connected apps",
            "ja": "接続アプリ一覧取得",
        },
        "note": {
            "en": "Permission to get a list of apps connected to the server",
            "ja": "サーバーに接続されたアプリの一覧を取得する",
        },
    },
)


class ServerExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        server.packet_dispatcher.register(
            REQUIRE_APPS_PACKET_TYPE,
        )
        server.permissions.register(
            SERVER_SHUTDOWN_PERMISSION,
            SERVER_APPS_READ_PERMISSION,
        )
        self.version_registry = self._server.registry.register(VERSION_REGISTRY_TYPE)
        self.apps = self._server.tables.register(APP_TABLE_TYPE)
        server.network.event.connected += self.on_connected
        server.network.event.disconnected += self.on_disconnected
        server.event.start += self.on_start
        server.endpoints.bind_endpoint(SHUTDOWN_ENDPOINT_TYPE, self.shutdown)
        server.packet_dispatcher.add_packet_handler(
            REQUIRE_APPS_PACKET_TYPE, self.handle_require_apps
        )
        self._app_waiters: dict[Identifier, list[WaitHandle]] = defaultdict(list)

    async def handle_require_apps(
        self, session: Session, app_ids: list[Identifier]
    ) -> None:
        for identifier in self._server.network._sessions.keys():
            if identifier not in app_ids:
                continue
            app_ids.remove(identifier)
        if len(app_ids) == 0:
            return

        ready_task = await session.create_ready_task(f"require_apps({app_ids})")

        waiter = WaitHandle(app_ids)
        for app_id in app_ids:
            self._app_waiters[app_id].append(waiter)
        await waiter.future
        ready_task.set()

    async def shutdown(self, session: Session, restart: bool = False) -> bool:
        await self._server.shutdown()
        self._server.loop.create_task(self._shutdown(restart))
        return True

    async def _shutdown(self, restart: bool = False) -> None:
        if restart:
            import os
            import sys

            os.execv(sys.executable, get_launch_command()["args"])
        else:
            self._server.loop.stop()

    async def on_start(self) -> None:
        await self.version_registry.set(__version__)
        await self.apps.clear()

    async def on_connected(self, session: Session) -> None:
        logger.info(f"Connected: {session.app.key()}")
        await self.apps.add(session.app)
        unlisten = session.event.ready.listen(self.on_session_ready)

        @session.event.disconnected.listen
        def on_disconnected(session: Session) -> None:
            unlisten()

    async def on_session_ready(self, session: Session) -> None:
        for waiter in self._app_waiters.get(session.app.id, []):
            waiter.ids.remove(session.app.id)
            if len(waiter.ids) == 0:
                waiter.future.set_result(True)

    async def on_disconnected(self, session: Session) -> None:
        logger.info(f"Disconnected: {session.app.key()}")
        await self.apps.remove(session.app)

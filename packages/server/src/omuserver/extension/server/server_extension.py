from __future__ import annotations

import asyncio
from asyncio import Future
from collections import defaultdict
from collections.abc import Callable
from typing import TYPE_CHECKING

from loguru import logger
from omu.errors import PermissionDenied
from omu.extension.server.packets import ConsolePacket
from omu.extension.server.server_extension import (
    APP_TABLE_TYPE,
    CONSOLE_GET_ENDPOINT_TYPE,
    CONSOLE_LISTEN_PACKET_TYPE,
    CONSOLE_PACKET_TYPE,
    REQUIRE_APPS_PACKET_TYPE,
    SERVER_CONSOLE_PERMISSION_ID,
    SHUTDOWN_ENDPOINT_TYPE,
    VERSION_REGISTRY_TYPE,
)
from omu.identifier import Identifier

from omuserver import __version__
from omuserver.helper import get_launch_command
from omuserver.server import Server
from omuserver.session import Session

from .permissions import (
    SERVER_APPS_READ_PERMISSION,
    SERVER_CONSOLE_PERMISSION,
    SERVER_SHUTDOWN_PERMISSION,
)

if TYPE_CHECKING:
    from loguru import Message


class WaitHandle:
    def __init__(self, ids: list[Identifier]):
        self.future = Future()
        self.ids = ids


class LogHandler:
    def __init__(
        self,
        callback: Callable[[str], None],
    ) -> None:
        self.callback = callback

    def write(self, message: Message) -> None:
        self.callback(message)


class ServerExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        server.packet_dispatcher.register(
            REQUIRE_APPS_PACKET_TYPE,
            CONSOLE_LISTEN_PACKET_TYPE,
        )
        server.permissions.register(
            SERVER_SHUTDOWN_PERMISSION,
            SERVER_APPS_READ_PERMISSION,
            SERVER_CONSOLE_PERMISSION,
        )
        self.version_registry = self._server.registry.register(VERSION_REGISTRY_TYPE)
        self.apps = self._server.tables.register(APP_TABLE_TYPE)
        server.network.event.connected += self.on_connected
        server.network.event.disconnected += self.on_disconnected
        server.event.start += self.on_start
        server.endpoints.bind_endpoint(
            SHUTDOWN_ENDPOINT_TYPE,
            self.handle_shutdown,
        )
        server.packet_dispatcher.add_packet_handler(
            REQUIRE_APPS_PACKET_TYPE, self.handle_require_apps
        )
        server.endpoints.bind_endpoint(
            CONSOLE_GET_ENDPOINT_TYPE, self.handle_console_get
        )
        server.packet_dispatcher.add_packet_handler(
            CONSOLE_LISTEN_PACKET_TYPE, self.handle_console_listen
        )
        self._app_waiters: dict[Identifier, list[WaitHandle]] = defaultdict(list)
        self._log_lines: list[str] = []
        self._log_listeners: list[Session] = []
        self._log_queue: list[str] = []
        self._log_event = asyncio.Event()
        logger.add(LogHandler(self._on_log))
        self._server.loop.create_task(self.log_task())

    def _on_log(self, message: str) -> None:
        self._log_queue.append(message)
        self._log_event.set()

    async def log_task(self) -> None:
        while True:
            await self._log_event.wait()
            self._log_event.clear()
            packet = ConsolePacket(self._log_queue)
            for session in self._log_listeners:
                if session.closed:
                    continue
                await session.send(CONSOLE_PACKET_TYPE, packet)
            self._log_lines.extend(self._log_queue)
            self._log_queue.clear()

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

    async def handle_shutdown(self, session: Session, restart: bool = False) -> bool:
        await self._server.shutdown()
        self._server.loop.create_task(self.shutdown(restart))
        return True

    async def shutdown(self, restart: bool = False) -> None:
        if restart:
            import os
            import sys

            os.execv(sys.executable, get_launch_command()["args"])
        else:
            self._server.loop.stop()

    async def handle_console_get(
        self, session: Session, line_count: int | None
    ) -> list[str]:
        if line_count is None:
            return self._log_lines
        return self._log_lines[-line_count:]

    async def handle_console_listen(self, session: Session, packet: None) -> None:
        if not self._server.permissions.has_permission(
            session, SERVER_CONSOLE_PERMISSION_ID
        ):
            msg = (
                f"Session {session} does not have permission "
                f"{SERVER_CONSOLE_PERMISSION_ID}"
            )
            raise PermissionDenied(msg)
        self._log_listeners.append(session)

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

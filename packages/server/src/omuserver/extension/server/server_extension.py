from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from omu.extension.server.server_extension import (
    APPS_TABLE_TYPE,
    SHUTDOWN_ENDPOINT_TYPE,
)
from omu.serializer import Serializer

from omuserver import __version__
from omuserver.helper import get_launch_command

if TYPE_CHECKING:
    from omuserver.server import Server
    from omuserver.session.session import Session


class ServerExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        server.network.listeners.connected += self.on_connected
        server.network.listeners.disconnected += self.on_disconnected
        server.listeners.start += self.on_start
        server.endpoints.bind_endpoint(SHUTDOWN_ENDPOINT_TYPE, self.shutdown)

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
        self.apps = await self._server.tables.register_table(APPS_TABLE_TYPE)
        version = await self._server.registry.create(
            "server:version", __version__, Serializer.json()
        )
        await version.set(__version__)
        directories = await self._server.registry.create(
            "server:directories", self._server.directories.to_json(), Serializer.json()
        )
        await directories.set(self._server.directories.to_json())
        await self.apps.clear()

    async def on_connected(self, session: Session) -> None:
        logger.info(f"Connected: {session.app.key()}")
        await self.apps.add(session.app)

    async def on_disconnected(self, session: Session) -> None:
        logger.info(f"Disconnected: {session.app.key()}")
        await self.apps.remove(session.app)

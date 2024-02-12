from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger
from omu.extension.server.server_extension import (
    AppsTableType,
    PrintTasksEndpointType,
    ShutdownEndpointType,
)

from omuserver import __version__
from omuserver.extension import Extension
from omuserver.extension.table import TableExtension
from omuserver.helper import get_launch_command
from omuserver.network import NetworkListener

if TYPE_CHECKING:
    from omuserver.server import Server
    from omuserver.session.session import Session


class ServerExtension(Extension, NetworkListener):
    def __init__(self, server: Server) -> None:
        self._server = server
        server.network.add_listener(self)
        server.endpoints.bind_endpoint(ShutdownEndpointType, self.shutdown)
        server.endpoints.bind_endpoint(PrintTasksEndpointType, self.print_tasks)

    async def print_tasks(self, session: Session, _) -> None:
        logger.info("Tasks:")
        for task in asyncio.all_tasks(self._server.loop):
            logger.info(task)

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

    @classmethod
    def create(cls, server: Server) -> ServerExtension:
        return cls(server)

    async def on_start(self) -> None:
        table = self._server.extensions.get(TableExtension)
        self.apps = await table.register_table(AppsTableType)
        await self._server.registry.store("server:version", __version__)
        await self._server.registry.store(
            "server:directories", self._server.directories.to_json()
        )
        await self.apps.clear()

    async def on_connected(self, session: Session) -> None:
        logger.info(f"Connected: {session.app.key()}")
        await self.apps.add(session.app)

    async def on_disconnected(self, session: Session) -> None:
        logger.info(f"Disconnected: {session.app.key()}")
        await self.apps.remove(session.app)

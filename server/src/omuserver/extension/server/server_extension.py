from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from omu.extension.server.server_extension import AppsTableType, ShutdownEndpointType

from omuserver import __version__
from omuserver.extension import Extension
from omuserver.extension.table import TableExtension
from omuserver.network import NetworkListener
from omuserver.server import ServerListener
from omuserver.utils.helper import get_launch_command

if TYPE_CHECKING:
    from omuserver.server import Server
    from omuserver.session.session import Session


class ServerExtension(Extension, NetworkListener, ServerListener):
    def __init__(self, server: Server) -> None:
        self._server = server
        table = server.extensions.get(TableExtension)
        self.apps = table.register_table(AppsTableType)
        server.network.add_listener(self)
        server.add_listener(self)
        server.endpoints.bind_endpoint(ShutdownEndpointType, self.shutdown)

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
        await self._server.registry.store("server:version", __version__)
        await self._server.registry.store(
            "server:directories", self._server.directories.to_json()
        )
        await self.apps.clear()

    async def on_connected(self, session: Session) -> None:
        logger.info(f"Connected: {session.app.key()}")
        await self.apps.add({session.app.key(): session.app})

    async def on_disconnected(self, session: Session) -> None:
        logger.info(f"Disconnected: {session.app.key()}")
        await self.apps.remove([session.app.key()])

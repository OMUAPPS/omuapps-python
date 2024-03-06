from __future__ import annotations
import asyncio
import json

from pathlib import Path
import threading
from typing import TYPE_CHECKING, Dict, Protocol, TypeGuard, TypedDict

from loguru import logger

from omuserver.extension import Extension
from omuserver.server import ServerListener

if TYPE_CHECKING:
    from omuserver.server import Server


class Plugin(Protocol):
    async def main(self) -> None: ...


class PluginMetadata(TypedDict):
    module: str


class PluginExtension(Extension, ServerListener):
    def __init__(self, server: Server) -> None:
        self._server = server
        self.plugins: Dict[str, Plugin] = {}
        server.add_listener(self)

    @classmethod
    def create(cls, server: Server) -> PluginExtension:
        return cls(server)

    async def on_server_start(self) -> None:
        await self._load_plugins()

    async def _load_plugins(self) -> None:
        for plugin in self._server.directories.plugins.iterdir():
            if not plugin.is_file():
                continue
            if plugin.name.startswith("_"):
                continue
            logger.info(f"Loading plugin: {plugin.name}")
            await self._load_plugin(plugin)

    def validate_plugin(self, plugin: Plugin) -> TypeGuard[Plugin]:
        main = getattr(plugin, "main", None)
        if main is None:
            raise ValueError(f"Plugin {plugin} does not have a main coroutine")
        if not asyncio.iscoroutinefunction(plugin.main):
            raise ValueError(f"Plugin {plugin} does not have a main coroutine")
        return True

    async def _load_plugin(self, path: Path) -> None:
        metadata = PluginMetadata(**json.loads((path).read_text()))
        plugin = __import__(metadata["module"])
        if not self.validate_plugin(plugin):
            return
        loop = asyncio.new_event_loop()
        loop.create_task(plugin.main())
        thread = threading.Thread(target=loop.run_forever, daemon=True, name=path.name)
        thread.start()

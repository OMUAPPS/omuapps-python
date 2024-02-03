from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Dict

from loguru import logger

from omuserver.extension import Extension
from omuserver.server import ServerListener

from .plugin import Plugin, ServerPlugin

if TYPE_CHECKING:
    from omuserver.server import Server


class PluginLoader:
    def __init__(self, server: Server) -> None:
        self._server = server

    def is_valid_plugin(self, path: Path) -> bool:
        if not path.is_dir():
            return False
        if not (path / "run.py").exists():
            return False
        return True

    async def load(self, path: Path) -> Plugin:
        if not self.is_valid_plugin(path):
            raise ValueError(f"Invalid plugin: {path}")
        return await ServerPlugin.create(path, self._server)


class PluginExtension(Extension, ServerListener):
    def __init__(self, server: Server) -> None:
        self._server = server
        self.plugins: Dict[str, Plugin] = {}
        self.loader = PluginLoader(server)
        server.add_listener(self)

    @classmethod
    def create(cls, server: Server) -> PluginExtension:
        return cls(server)

    async def on_start(self) -> None:
        await self._load_plugins()

    async def _load_plugins(self) -> None:
        for plugin in self._server.directories.plugins.iterdir():
            if plugin.name.startswith("."):
                continue
            if not self.loader.is_valid_plugin(plugin):
                continue
            logger.info(f"Loading plugin: {plugin.name}")
            await self._load_plugin(plugin)

    async def _load_plugin(self, path: Path) -> None:
        plugin = await self.loader.load(path)
        self.plugins[path.name] = plugin
        await plugin.start()

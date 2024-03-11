from __future__ import annotations
import asyncio
import json

from importlib.util import find_spec
from pathlib import Path
import re
import subprocess
import sys
import threading
from typing import (
    TYPE_CHECKING,
    Dict,
    NotRequired,
    Protocol,
    TypeGuard,
    TypedDict,
)

from loguru import logger

from omuserver.extension import Extension

from omu.plugin import Plugin

from omuserver.extension.plugin.plugin_connection import PluginConnection
from omuserver.extension.plugin.plugin_session import PluginSession

if TYPE_CHECKING:
    from omuserver.server import Server


class PluginModule(Protocol):
    def get_plugin(self) -> Plugin: ...


class PluginMetadata(TypedDict):
    dependencies: Dict[str, str]
    module: str
    isolated: NotRequired[bool]


class PluginExtension(Extension):
    def __init__(self, server: Server) -> None:
        self._server = server
        self.plugins: Dict[str, PluginMetadata] = {}
        server.listeners.start += self.on_server_start

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
            metadata = self._load_plugin(plugin)
            self.plugins[metadata["module"]] = metadata
        await self.install_dependencies()
        await self.run_plugins()

    def _load_plugin(self, path: Path) -> PluginMetadata:
        metadata = PluginMetadata(**json.loads(path.read_text()))
        invalid_dependencies = []
        for dependency in metadata.get("dependencies", []):
            if not re.match(r"^[a-zA-Z0-9_-]+$", dependency):
                invalid_dependencies.append(dependency)
        if invalid_dependencies:
            raise ValueError(f"Invalid dependencies in {path}: {invalid_dependencies}")
        if not re.match(r"^[a-zA-Z0-9_-]+$", metadata["module"]):
            raise ValueError(f"Invalid module in {path}: {metadata['module']}")
        return metadata

    async def install_dependencies(self) -> None:
        # https://stackoverflow.com/a/44210735
        dependencies: dict[str, str] = {}
        for metadata in self.plugins.values():
            dependencies.update(metadata["dependencies"])
        to_install: Dict[str, str] = {}
        for dependency, version in dependencies.items():
            spec = find_spec(dependency)
            if spec is None:
                to_install[dependency] = version
        if len(to_install) == 0:
            return
        logger.info(f"Installing dependencies {to_install}")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                *to_install,
            ],
            check=True,
        )

    async def run_plugins(self) -> None:
        for metadata in self.plugins.values():
            await self.run_plugin(metadata)

    def validate_plugin_module(self, module: PluginModule) -> TypeGuard[PluginModule]:
        get_plugin = getattr(module, "get_plugin", None)
        if get_plugin is None:
            raise ValueError(f"Plugin {get_plugin} does not have a get_plugin method")
        return True

    async def run_plugin(self, metadata: PluginMetadata):
        module = __import__(metadata["module"])
        if not self.validate_plugin_module(module):
            return
        plugin = module.get_plugin()
        client = plugin.client
        if metadata.get("isolated"):
            loop = asyncio.new_event_loop()
            loop.create_task(client.start())
            thread = threading.Thread(
                target=loop.run_forever,
                daemon=True,
                name=f"Plugin {metadata['module']}",
            )
            thread.start()
        else:
            connection = PluginConnection()
            client.network.set_connection(connection)
            await client.start()
            session = await PluginSession.create(self._server, connection)
            self._server.loop.create_task(self._server.network.process_session(session))

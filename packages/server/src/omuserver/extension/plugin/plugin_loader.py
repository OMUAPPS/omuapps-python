from __future__ import annotations

import asyncio
import importlib.metadata
import importlib.util
import sys
from multiprocessing import Process
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Mapping,
    Protocol,
)

from loguru import logger
from omu import Address
from omu.network.websocket_connection import WebsocketsConnection
from omu.plugin import Plugin
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from omuserver.session import Session

from .plugin_connection import PluginConnection
from .plugin_session_connection import PluginSessionConnection

if TYPE_CHECKING:
    from omuserver.server import Server

PLUGIN_GROUP = "omu.plugins"


class PluginModule(Protocol):
    plugin: Plugin


class DependencyResolver:
    def __init__(self) -> None:
        self._dependencies: Dict[str, SpecifierSet] = {}

    def format_dependencies(
        self, dependencies: Mapping[str, SpecifierSet | None]
    ) -> List[str]:
        args = []
        for dependency, specifier in dependencies.items():
            if specifier is not None:
                args.append(f"{dependency}{specifier}")
            else:
                args.append(dependency)
        return args

    async def _install(self, to_install: Mapping[str, SpecifierSet]) -> None:
        if len(to_install) == 0:
            return
        logger.info(
            "Installing dependencies " + ", ".join(self.format_dependencies(to_install))
        )
        install_process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            *self.format_dependencies(to_install),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await install_process.communicate()
        if install_process.returncode != 0:
            logger.error(f"Error installing dependencies: {stderr}")
            return
        logger.info(f"Installed dependencies: {stdout}")

    async def _update(self, to_update: Mapping[str, SpecifierSet]) -> None:
        if len(to_update) == 0:
            return
        logger.info(
            "Updating dependencies " + ", ".join(self.format_dependencies(to_update))
        )
        update_process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            *[
                f"{dependency}{specifier}"
                for dependency, specifier in to_update.items()
            ],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await update_process.communicate()
        if update_process.returncode != 0:
            logger.error(f"Error updating dependencies: {stderr}")
            return
        logger.info(f"Updated dependencies: {stdout}")

    def add_dependencies(self, dependencies: Mapping[str, SpecifierSet | None]) -> bool:
        changed = False
        for dependency, specifier in dependencies.items():
            if dependency not in self._dependencies:
                self._dependencies[dependency] = SpecifierSet()
                changed = True
                continue
            if specifier is not None:
                specifier_set = self._dependencies[dependency]
                if specifier_set != specifier:
                    changed = True
                specifier_set &= specifier
                continue
        return changed

    async def resolve(self):
        to_install: Dict[str, SpecifierSet] = {}
        to_update: Dict[str, SpecifierSet] = {}
        skipped: Dict[str, SpecifierSet] = {}
        packages_distributions: Mapping[str, importlib.metadata.Distribution] = {
            dist.name: dist for dist in importlib.metadata.distributions()
        }
        for dependency, specifier in self._dependencies.items():
            package = packages_distributions.get(dependency)
            if package is None:
                to_install[dependency] = specifier
                continue
            distribution = packages_distributions[package.name]
            installed_version = Version(distribution.version)
            specifier_set = self._dependencies[dependency]
            if installed_version in specifier_set:
                skipped[dependency] = specifier_set
                continue
            to_update[dependency] = specifier_set

        await self._install(to_install)
        await self._update(to_update)
        logger.info(
            f"Skipped dependencies: {", ".join(self.format_dependencies(skipped))}"
        )


class PluginLoader:
    def __init__(self, server: Server) -> None:
        self._server = server
        self.plugins: Dict[str, Plugin] = {}

    async def load_plugins(self) -> None:
        await self.run_plugins()

    async def run_plugins(self):
        entry_points = importlib.metadata.entry_points(group=PLUGIN_GROUP)
        for entry_point in entry_points:
            if entry_point.dist is None:
                raise ValueError(f"Invalid plugin: {entry_point} has no distribution")
            plugin_key = entry_point.dist.name
            if plugin_key in self.plugins:
                raise ValueError(f"Duplicate plugin: {entry_point}")
            plugin = self.load_plugin_from_entry_point(entry_point)
            self.plugins[plugin_key] = plugin
            await self.run_plugin(plugin)

    async def load_updated_plugins(self):
        entry_points = importlib.metadata.entry_points(group=PLUGIN_GROUP)
        for entry_point in entry_points:
            if entry_point.dist is None:
                raise ValueError(f"Invalid plugin: {entry_point} has no distribution")
            plugin_key = entry_point.dist.name
            if plugin_key in self.plugins:
                continue
            plugin = self.load_plugin_from_entry_point(entry_point)
            self.plugins[plugin_key] = plugin
            await self.run_plugin(plugin)

    async def run_plugin(self, plugin: Plugin):
        if plugin.isolated:
            process = Process(
                target=run_plugin_process,
                args=(
                    plugin,
                    self._server.address,
                ),
                daemon=True,
            )
            process.start()
        else:
            plugin_client = plugin.get_client()
            connection = PluginConnection()
            plugin_client.network.set_connection(connection)
            await plugin_client.start()
            session_connection = PluginSessionConnection(connection)
            session = await Session.from_connection(
                self._server,
                self._server.packet_dispatcher.packet_mapper,
                session_connection,
            )
            self._server.loop.create_task(self._server.network.process_session(session))

    def load_plugin_from_entry_point(
        self, entry_point: importlib.metadata.EntryPoint
    ) -> Plugin:
        plugin = entry_point.load()
        if not isinstance(plugin, Plugin):
            raise ValueError(f"Invalid plugin: {plugin} is not a Plugin")
        return plugin


def handle_exception(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    logger.error(context["message"])
    exception = context.get("exception")
    if exception:
        raise exception


def run_plugin_process(
    plugin: Plugin,
    address: Address,
) -> None:
    client = plugin.get_client()
    connection = WebsocketsConnection(client, address)
    client.network.set_connection(connection)
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    loop.run_until_complete(client.start())
    loop.run_forever()
    loop.close()

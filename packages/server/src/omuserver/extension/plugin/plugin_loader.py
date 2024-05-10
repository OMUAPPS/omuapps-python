from __future__ import annotations

import asyncio
import importlib.metadata
import importlib.util
import sys
import tempfile
from collections.abc import Mapping
from multiprocessing import Process
from typing import (
    Protocol,
)

import aiohttp
import uv
from loguru import logger
from omu.address import Address
from omu.app import App
from omu.client.token import TokenProvider
from omu.extension.plugin import PackageInfo
from omu.extension.plugin.plugin import PluginPackageInfo
from omu.network.websocket_connection import WebsocketsConnection
from omu.plugin import Plugin
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from omuserver.server import Server
from omuserver.session import Session

from .plugin_connection import PluginConnection
from .plugin_session_connection import PluginSessionConnection

PLUGIN_GROUP = "omu.plugins"


class PluginModule(Protocol):
    plugin: Plugin


class DependencyResolver:
    def __init__(self) -> None:
        self._dependencies: dict[str, SpecifierSet] = {}

    async def fetch_package_info(self, package: str) -> PackageInfo:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://pypi.org/pypi/{package}/json") as response:
                return await response.json()

    async def get_installed_package_info(
        self, package: str
    ) -> PluginPackageInfo | None:
        try:
            package_info = importlib.metadata.distribution(package)
        except importlib.metadata.PackageNotFoundError:
            return None
        return PluginPackageInfo(
            package=package_info.name,
            version=package_info.version,
        )

    def format_dependencies(
        self, dependencies: Mapping[str, SpecifierSet | None]
    ) -> list[str]:
        args = []
        for dependency, specifier in dependencies.items():
            if specifier is not None:
                args.append(f"{dependency}{specifier}")
            else:
                args.append(dependency)
        return args

    async def update_requirements(self, requirements: dict[str, SpecifierSet]) -> None:
        if len(requirements) == 0:
            return
        with tempfile.NamedTemporaryFile(mode="wb", delete=True) as req_file:
            dependency_lines = self.format_dependencies(requirements)
            req_file.write("\n".join(dependency_lines).encode("utf-8"))
            req_file.flush()
            process = await asyncio.create_subprocess_exec(
                uv.find_uv_bin(),
                "pip",
                "install",
                "--upgrade",
                "-r",
                req_file.name,
                "--python",
                sys.executable,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error(f"Error running uv command: {stderr}")
            return
        logger.info(f"Ran uv command: {stdout or stderr}")

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
        requirements: dict[str, SpecifierSet] = {}
        skipped: dict[str, SpecifierSet] = {}
        packages_distributions: Mapping[str, importlib.metadata.Distribution] = {
            dist.name: dist for dist in importlib.metadata.distributions()
        }
        for dependency, specifier in self._dependencies.items():
            package = packages_distributions.get(dependency)
            if package is None:
                requirements[dependency] = specifier
                continue
            distribution = packages_distributions[package.name]
            installed_version = Version(distribution.version)
            specifier_set = self._dependencies[dependency]
            if installed_version in specifier_set:
                skipped[dependency] = specifier_set
                continue
            requirements[dependency] = specifier_set

        await self.update_requirements(requirements)
        logger.info(
            f"Skipped dependencies: {", ".join(self.format_dependencies(skipped))}"
        )


class PluginLoader:
    def __init__(self, server: Server) -> None:
        self._server = server
        self.plugins: dict[str, Plugin] = {}
        server.event.start += self.handle_server_start
        server.event.stop += self.handle_server_stop

    async def handle_server_start(self) -> None:
        for plugin in self.plugins.values():
            if plugin.on_start_server is not None:
                await plugin.on_start_server(self._server)

    async def handle_server_stop(self) -> None:
        for plugin in self.plugins.values():
            if plugin.on_stop_server is not None:
                await plugin.on_stop_server(self._server)

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
        token = await self._server.security.generate_plugin_token()
        if plugin.isolated:
            process = Process(
                target=run_plugin_isolated,
                args=(
                    plugin,
                    self._server.address,
                    token,
                ),
                daemon=True,
            )
            process.start()
        else:
            if plugin.get_client is not None:
                plugin_client = plugin.get_client()
                connection = PluginConnection()
                plugin_client.network.set_connection(connection)
                plugin_client.network.set_token_provider(PluginTokenProvider(token))
                await plugin_client.start()
                session_connection = PluginSessionConnection(connection)
                session = await Session.from_connection(
                    self._server,
                    self._server.packet_dispatcher.packet_mapper,
                    session_connection,
                )
                self._server.loop.create_task(
                    self._server.network.process_session(session)
                )

    def load_plugin_from_entry_point(
        self, entry_point: importlib.metadata.EntryPoint
    ) -> Plugin:
        plugin = entry_point.load()
        if not isinstance(plugin, Plugin):
            raise ValueError(f"Invalid plugin: {plugin} is not a Plugin")
        return plugin


class PluginTokenProvider(TokenProvider):
    def __init__(self, token: str):
        self._token = token

    def get(self, server_address: Address, app: App) -> str | None:
        return self._token

    def store(self, server_address: Address, app: App, token: str) -> None:
        raise NotImplementedError


def handle_exception(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    logger.error(context["message"])
    exception = context.get("exception")
    if exception:
        raise exception


def run_plugin_isolated(
    plugin: Plugin,
    address: Address,
    token: str,
) -> None:
    if plugin.get_client is None:
        raise ValueError(f"Invalid plugin: {plugin} has no client")
    client = plugin.get_client()
    connection = WebsocketsConnection(client, address)
    client.network.set_connection(connection)
    client.network.set_token_provider(PluginTokenProvider(token))
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    loop.run_until_complete(client.start())
    loop.run_forever()
    loop.close()

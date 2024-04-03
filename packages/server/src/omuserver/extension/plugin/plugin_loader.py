from __future__ import annotations

import asyncio
import importlib.metadata
import importlib.util
import json
import re
import sys
import time
import traceback
from dataclasses import dataclass
from multiprocessing import Process
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Dict,
    List,
    Mapping,
    Protocol,
    TypeGuard,
)

from loguru import logger
from omu import Address
from omu.extension.plugin import PluginMetadata
from omu.network.websocket_connection import WebsocketsConnection
from omu.plugin import Plugin
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from omuserver.session import Session

from .plugin_connection import PluginConnection
from .plugin_session_connection import PluginSessionConnection

if TYPE_CHECKING:
    from omuserver.server import Server


class PluginModule(Protocol):
    plugin: Plugin


@dataclass(frozen=True)
class PluginEntry:
    dependencies: Mapping[str, SpecifierSet | None]
    module: str

    @classmethod
    def validate(cls, metadata: PluginMetadata) -> PluginEntry:
        invalid_dependencies: Dict[str, str | None] = {}
        dependencies: Dict[str, SpecifierSet | None] = {}
        for dependency, specifier in metadata.get("dependencies", []).items():
            if not re.match(r"^[a-zA-Z0-9_-]+$", dependency):
                invalid_dependencies[dependency] = specifier
            if specifier is None or specifier == "":
                dependencies[dependency] = None
            else:
                dependencies[dependency] = SpecifierSet(specifier)
        if invalid_dependencies:
            raise ValueError(f"Invalid dependencies: {invalid_dependencies}")
        if "module" not in metadata or not re.match(
            r"^[a-zA-Z0-9_-]+$", metadata["module"]
        ):
            raise ValueError(f"Invalid module: {metadata.get('module')}")
        return cls(
            dependencies=dependencies,
            module=metadata["module"],
        )

    @classmethod
    def _parse_plugin(cls, path: Path) -> PluginEntry:
        data = json.loads(path.read_text())
        metadata = PluginEntry.validate(data)
        if metadata is None:
            raise ValueError(f"Invalid metadata in plugin {path}")
        return metadata


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

    def add_dependencies(self, dependencies: Mapping[str, SpecifierSet | None]):
        for dependency, specifier in dependencies.items():
            if dependency not in self._dependencies:
                self._dependencies[dependency] = SpecifierSet()
                continue
            if specifier is not None:
                specifier_set = self._dependencies[dependency]
                specifier_set &= specifier
                continue

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
        self.dependency_resolver = DependencyResolver()
        self.plugins: Dict[Path, PluginEntry] = {}

    async def load_plugins(self) -> None:
        self.register_plugins()
        await self.resolve_plugin_dependencies()
        await self.run_plugins()

    def register_plugins(self):
        for plugin in self._server.directories.plugins.iterdir():
            if not plugin.is_file():
                continue
            if plugin.name.startswith("_"):
                continue
            logger.info(f"Loading plugin: {plugin.name}")
            metadata = PluginEntry._parse_plugin(plugin)
            self.plugins[plugin] = metadata

    async def resolve_plugin_dependencies(self) -> None:
        for metadata in self.plugins.values():
            self.dependency_resolver.add_dependencies(metadata.dependencies)
        await self.dependency_resolver.resolve()

    async def run_plugins(self) -> None:
        for metadata in self.plugins.values():
            try:
                await self.run_plugin(metadata)
            except Exception as e:
                traceback.print_exc()
                logger.error(f"Error running plugin {metadata.module}: {e}")

    async def run_plugin(self, metadata: PluginEntry):
        module = __import__(metadata.module)
        if not validate_plugin_module(module):
            return
        plugin = module.plugin
        if plugin.isolated:
            start_time = time.time()
            process = Process(
                target=run_plugin_process,
                args=(
                    plugin,
                    self._server.address,
                    start_time,
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


def validate_plugin_module(module: PluginModule) -> TypeGuard[PluginModule]:
    plugin = getattr(module, "plugin", None)
    return isinstance(plugin, Plugin)


def handle_exception(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    logger.error(context["message"])
    exception = context.get("exception")
    if exception:
        raise exception


def run_plugin_process(
    plugin: Plugin,
    address: Address,
    start_time: float,
) -> None:
    a = time.time() - start_time
    client = plugin.get_client()
    logger.info(a)
    connection = WebsocketsConnection(client, address)
    client.network.set_connection(connection)
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    loop.run_until_complete(client.start())
    loop.run_forever()
    loop.close()

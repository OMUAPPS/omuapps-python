from __future__ import annotations

import asyncio
import importlib.metadata
import importlib.util
import json
import re
import sys
import traceback
from dataclasses import dataclass
from multiprocessing import Process
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    Protocol,
    TypeGuard,
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


class PluginModule(Protocol):
    def get_plugin(self) -> Plugin: ...


@dataclass(frozen=True)
class PluginMetadata:
    dependencies: Mapping[str, SpecifierSet | None]
    module: str
    isolated: bool = False

    @classmethod
    def validate(cls, metadata: Dict[str, Any]) -> PluginMetadata | None:
        invalid_dependencies: Dict[str, str] = {}
        dependencies: Dict[str, SpecifierSet | None] = metadata.get("dependencies", {})
        for dependency, specifier in metadata.get("dependencies", []).items():
            if not re.match(r"^[a-zA-Z0-9_-]+$", dependency):
                invalid_dependencies[dependency] = specifier
            if specifier == "":
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
            isolated=metadata.get("isolated", False),
        )


class PluginExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        self.plugins: Dict[Path, PluginMetadata] = {}
        server.listeners.start += self.on_server_start

    async def on_server_start(self) -> None:
        await self._load_plugins()

    async def _load_plugins(self) -> None:
        self.register_plugins()
        await self.install_dependencies()
        await self.run_plugins()

    def register_plugins(self):
        for plugin in self._server.directories.plugins.iterdir():
            if not plugin.is_file():
                continue
            if plugin.name.startswith("_"):
                continue
            logger.info(f"Loading plugin: {plugin.name}")
            metadata = self._load_plugin(plugin)
            self.plugins[plugin] = metadata

    def _load_plugin(self, path: Path) -> PluginMetadata:
        data = json.loads(path.read_text())
        metadata = PluginMetadata.validate(data)
        if metadata is None:
            raise ValueError(f"Invalid metadata in plugin {path}")
        return metadata

    def generate_dependencies_str(
        self, dependencies: Mapping[str, SpecifierSet | None]
    ) -> List[str]:
        args = []
        for dependency, specifier in dependencies.items():
            if specifier is not None:
                args.append(f"{dependency}{specifier}")
            else:
                args.append(dependency)
        return args

    async def install_dependencies(self) -> None:
        # https://stackoverflow.com/a/44210735
        dependencies: Dict[str, SpecifierSet] = {}
        for plugin in self.plugins.values():
            for dependency, specifier in plugin.dependencies.items():
                if dependency not in dependencies:
                    dependencies[dependency] = SpecifierSet()
                    continue
                if specifier is not None:
                    specifier_set = dependencies[dependency]
                    specifier_set &= specifier
                    continue

        packages_distributions: Mapping[str, importlib.metadata.Distribution] = {
            dist.name: dist for dist in importlib.metadata.distributions()
        }

        to_install: Dict[str, SpecifierSet] = {}
        to_update: Dict[str, SpecifierSet] = {}
        skipped: Dict[str, SpecifierSet] = {}
        for dependency, specifier in dependencies.items():
            package = packages_distributions.get(dependency)
            if package is None:
                to_install[dependency] = specifier
                continue
            distribution = packages_distributions[package.name]
            installed_version = Version(distribution.version)
            specifier_set = dependencies[dependency]
            if installed_version in specifier_set:
                skipped[dependency] = specifier_set
                continue
            to_update[dependency] = specifier_set
        if len(to_install) > 0:
            logger.info(
                "Installing dependencies "
                + " ".join(self.generate_dependencies_str(to_install))
            )
            install_process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                *self.generate_dependencies_str(to_install),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await install_process.communicate()
            if install_process.returncode != 0:
                logger.error(f"Error installing dependencies: {stderr}")
                return
            logger.info(f"Installed dependencies: {stdout}")
        if len(to_update) > 0:
            logger.info(
                "Updating dependencies "
                + " ".join(self.generate_dependencies_str(to_update))
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
        logger.info(
            f"Skipped dependencies: {" ".join(self.generate_dependencies_str(skipped))}"
        )

    async def run_plugins(self) -> None:
        for metadata in self.plugins.values():
            try:
                await self.run_plugin(metadata)
            except Exception as e:
                traceback.print_exc()
                logger.error(f"Error running plugin {metadata.module}: {e}")

    async def run_plugin(self, metadata: PluginMetadata):
        if metadata.isolated:
            process = Process(
                target=run_plugin_process,
                args=(
                    metadata,
                    Address(
                        "127.0.0.1",
                        self._server.address.port,
                    ),
                ),
                daemon=True,
            )
            process.start()
        else:
            module = __import__(metadata.module)
            if not validate_plugin_module(module):
                return
            plugin = module.get_plugin()
            client = plugin.client
            connection = PluginConnection()
            client.network.set_connection(connection)
            await client.start()
            session_connection = PluginSessionConnection(connection)
            session = await Session.from_connection(
                self._server,
                self._server.packet_dispatcher.packet_mapper,
                session_connection,
            )
            self._server.loop.create_task(self._server.network.process_session(session))


def validate_plugin_module(module: PluginModule) -> TypeGuard[PluginModule]:
    get_plugin = getattr(module, "get_plugin", None)
    if get_plugin is None:
        raise ValueError(f"Plugin {get_plugin} does not have a get_plugin method")
    return True


def handle_exception(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    logger.error(context["message"])
    exception = context.get("exception")
    if exception:
        raise exception


def run_plugin_process(
    metadata: PluginMetadata,
    address: Address,
) -> None:
    module = __import__(metadata.module)
    if not validate_plugin_module(module):
        raise ValueError(f"Invalid plugin module {metadata.module}")
    plugin = module.get_plugin()
    client = plugin.client
    connection = WebsocketsConnection(client, address)
    client.network.set_connection(connection)
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    loop.run_until_complete(client.start())
    loop.run_forever()
    loop.close()

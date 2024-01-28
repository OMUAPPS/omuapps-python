from __future__ import annotations

import abc
import importlib.util
import inspect
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from .plugin import Plugin

if TYPE_CHECKING:
    from omuserver.server import Server


class ServerModule(abc.ABC):
    @abc.abstractmethod
    async def main(self) -> None:
        ...


class ServerPlugin(Plugin):
    def __init__(self, path: Path, server: Server) -> None:
        self._path = path
        self._server = server
        self._module: ServerModule | None = None

    @classmethod
    async def create(cls, path: Path, server: Server) -> ServerPlugin:
        if not (path / "run.py").is_file():
            raise ValueError(f"{path} does not have a run.py file")
        return cls(path, server)

    def _validate_module(self, module: ModuleType) -> ServerModule:
        if not hasattr(module, "main") or not inspect.iscoroutinefunction(module.main):
            raise ValueError(f"{module} does not have a main function")
        return module  # type: ignore

    def _load_module(self) -> ServerModule:
        path = self._path / "run.py"
        spec = importlib.util.spec_from_file_location(path.stem, path)
        assert spec
        module = importlib.util.module_from_spec(spec)
        loader = spec.loader
        if not loader:
            raise AssertionError
        loader.exec_module(module)
        self._module = self._validate_module(module)
        return self._module

    async def start(self) -> None:
        module = self._load_module()
        await module.main()

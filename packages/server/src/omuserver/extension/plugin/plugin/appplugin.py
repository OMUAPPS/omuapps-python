from __future__ import annotations

import abc
import importlib.util
import inspect
import subprocess
import sys
from pathlib import Path
from types import ModuleType

from omuserver.server import Server

from .plugin import Plugin


class ServerModule(abc.ABC):
    @abc.abstractmethod
    async def main(self) -> None:
        ...


class ServerPlugin(Plugin):
    def __init__(self, path: Path, server: Server) -> None:
        self._path = path
        self._server = server
        self._process: subprocess.Popen[bytes] | None = None

    @classmethod
    async def create(cls, path: Path, server: Server) -> ServerPlugin:
        return cls(path, server)

    def _validate_module(self, module: ModuleType) -> ServerModule:
        if not hasattr(module, "main") or not inspect.iscoroutinefunction(module.main):
            raise ValueError(f"{module} does not have a main function")
        return module  # type: ignore

    def _load_module(self) -> ServerModule:
        path = self._path / "server.py"
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
        self._process = subprocess.Popen(
            [sys.executable, str(self._path / "main.py")],
            cwd=self._path,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    async def unload(self) -> None:
        raise NotImplementedError

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from omuserver.server import Server

    from .extension import Extension


class ExtensionRegistry(abc.ABC):
    @abc.abstractmethod
    def register[T: Extension](self, extension: type[T]) -> T:
        ...

    @abc.abstractmethod
    def get[T: Extension](self, extension: type[T]) -> T:
        ...


class ExtensionRegistryServer(ExtensionRegistry):
    def __init__(self, server: Server) -> None:
        self._server = server
        self._extensions: Dict[type[Extension], Extension] = {}

    def register[T: Extension](self, extension: type[T]) -> T:
        if extension in self._extensions:
            raise ValueError(f"Extension {extension} already registered")
        instance = extension.create(self._server)
        self._extensions[extension] = instance
        return instance

    def get[T: Extension](self, extension: type[T]) -> T:
        if extension not in self._extensions:
            raise ValueError(f"Extension {extension} not registered")
        instance = self._extensions[extension]
        if not isinstance(instance, extension):
            raise ValueError(f"Extension {extension} not registered")
        return instance

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
        self.server = server
        self.extensions: Dict[type[Extension], Extension] = {}

    def register[T: Extension](self, extension: type[T]) -> T:
        if extension in self.extensions:
            raise ValueError(f"Extension {extension} already registered")
        new_extension = extension.create(self.server)
        self.extensions[extension] = new_extension
        return new_extension

    def get[T: Extension](self, extension: type[T]) -> T:
        if extension not in self.extensions:
            raise ValueError(f"Extension {extension} not registered")
        instance = self.extensions[extension]
        if not isinstance(instance, extension):
            raise ValueError(f"Extension {extension} not registered")
        return instance

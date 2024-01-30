from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from omu.client import Client
    from omu.extension import Extension, ExtensionType


class ExtensionRegistry(abc.ABC):
    @abc.abstractmethod
    def register[T: Extension](self, type: ExtensionType[T]) -> T:
        ...

    @abc.abstractmethod
    def register_all(self, *types: ExtensionType) -> None:
        ...

    @abc.abstractmethod
    def get[Ext: Extension](self, extension_type: ExtensionType[Ext]) -> Ext:
        ...

    @abc.abstractmethod
    def has[Ext: Extension](self, extension_type: ExtensionType[Ext]) -> bool:
        ...


class ExtensionRegistryImpl(ExtensionRegistry):
    def __init__(self, client: Client) -> None:
        self._client = client
        self._extensions: Dict[str, Extension] = {}

    def register[T: Extension](self, type: ExtensionType[T]) -> T:
        if self.has(type):
            raise ValueError(f"Extension type {type} already registered")
        for dependency in type.dependencies():
            if not self.has(dependency):
                raise ValueError(
                    f"Extension type {type} depends on {dependency} which is not registered"
                )
        extension = type.create(self._client)
        self._extensions[type.key] = extension
        return extension

    def register_all(self, *types: ExtensionType) -> None:
        for type in types:
            self.register(type)

    def get[Ext: Extension](self, extension_type: ExtensionType[Ext]) -> Ext:
        if not self.has(extension_type):
            raise ValueError(f"Extension type {extension_type} not registered")
        extension: Ext = self._extensions[extension_type.key]  # type: ignore
        return extension

    def has[Ext: Extension](self, extension_type: ExtensionType[Ext]) -> bool:
        return extension_type.key in self._extensions

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Callable

from omu.helper import Coro
from omu.identifier import Identifier
from omu.serializer import Serializable, Serializer


@dataclass(frozen=True)
class RegistryType[T]:
    identifier: Identifier
    default_value: T
    serializer: Serializable[T, bytes]

    @classmethod
    def create_json(
        cls,
        identifier: Identifier,
        name: str,
        default_value: T,
    ) -> RegistryType[T]:
        return cls(identifier / name, default_value, Serializer.json())

    @classmethod
    def create_serialized(
        cls,
        identifier: Identifier,
        name: str,
        default_value: T,
        serializer: Serializable[T, bytes],
    ) -> RegistryType[T]:
        return cls(identifier / name, default_value, serializer)


class Registry[T](abc.ABC):
    @abc.abstractmethod
    async def get(self) -> T: ...

    @abc.abstractmethod
    async def update(self, handler: Coro[[T], T]) -> None: ...

    @abc.abstractmethod
    def listen(self, handler: Coro[[T], None]) -> Callable[[], None]: ...

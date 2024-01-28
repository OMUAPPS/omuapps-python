from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Callable, List

if TYPE_CHECKING:
    from omu.client import Client


class Extension(abc.ABC):
    pass


class ExtensionType[T: Extension]:
    def __init__(
        self,
        key: str,
        create: Callable[[Client], T],
        dependencies: List[ExtensionType],
    ):
        self._key = key
        self._create = create
        self._dependencies = dependencies

    @property
    def key(self) -> str:
        return self._key

    def create(self, client: Client) -> T:
        return self._create(client)

    def dependencies(self) -> List[ExtensionType]:
        return self._dependencies


def define_extension_type[T: Extension](
    key: str,
    create: Callable[[Client], T],
    dependencies: Callable[[], List[ExtensionType]],
):
    return ExtensionType(key, create, dependencies())

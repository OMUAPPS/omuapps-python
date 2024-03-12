from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Callable, List

from omu.identifier import Identifier

if TYPE_CHECKING:
    from omu.client import Client


class Extension(abc.ABC):
    pass


class ExtensionType[T: Extension](Identifier):
    name: str
    create: Callable[[Client], T]
    dependencies: Callable[[], List[ExtensionType]]

    def __init__(
        self,
        name: str,
        create: Callable[[Client], T],
        dependencies: Callable[[], List[ExtensionType]],
    ) -> None:
        super().__init__("ext", name)
        self.name = name
        self.create = create
        self.dependencies = dependencies

    def key(self) -> str:
        return self.name

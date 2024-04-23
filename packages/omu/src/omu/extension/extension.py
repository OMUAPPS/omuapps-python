from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Callable, List

from pydantic import BaseModel

from omu.identifier import Identifier

if TYPE_CHECKING:
    from omu.client import Client


class Extension(abc.ABC):
    pass


class ExtensionType[T: Extension](BaseModel):
    name: str
    create: Callable[[Client], T]
    dependencies: Callable[[], List[ExtensionType]]

    def key(self) -> str:
        return self.name

    def __truediv__(self, name: str) -> Identifier:
        return Identifier(namespace="ext", path=(self.name, name))

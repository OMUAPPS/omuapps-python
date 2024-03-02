from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, List

if TYPE_CHECKING:
    from omu.client import Client


class Extension(abc.ABC):
    pass


@dataclass
class ExtensionType[T: Extension]:
    name: str
    create: Callable[[Client], T]
    dependencies: Callable[[], List[ExtensionType]]

    def key(self) -> str:
        return self.name

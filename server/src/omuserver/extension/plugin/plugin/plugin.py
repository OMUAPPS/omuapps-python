from __future__ import annotations

import abc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from omuserver.server import Server


class Plugin(abc.ABC):
    @classmethod
    @abc.abstractmethod
    async def create(cls, path: Path, server: Server) -> Plugin:
        ...

    @abc.abstractmethod
    async def start(self) -> None:
        ...

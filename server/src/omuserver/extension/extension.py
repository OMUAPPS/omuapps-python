from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    from omuserver.server import Server


class Extension(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def create(cls, server: Server) -> Self:
        raise NotImplementedError

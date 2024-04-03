from dataclasses import dataclass
from typing import Callable

from .client import Client


@dataclass(frozen=True)
class Plugin:
    get_client: Callable[[], Client]
    isolated: bool = False

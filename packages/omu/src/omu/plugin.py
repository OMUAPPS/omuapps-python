from dataclasses import dataclass
from typing import Final

from omu import Client


@dataclass
class Plugin:
    client: Final[Client]

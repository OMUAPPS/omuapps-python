from dataclasses import dataclass

from omu import Client


@dataclass(frozen=True)
class Plugin:
    client: Client

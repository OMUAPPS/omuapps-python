from dataclasses import dataclass

from .client import Client


@dataclass(frozen=True)
class Plugin:
    client: Client

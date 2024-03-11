from dataclasses import dataclass

from omu import Client


@dataclass
class Plugin:
    client: Client

from dataclasses import dataclass
from typing import Final


@dataclass
class Address:
    host: Final[str]
    port: Final[int]
    secure: Final[bool] = False

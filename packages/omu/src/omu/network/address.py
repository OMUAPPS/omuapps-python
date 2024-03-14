from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    host: str
    port: int
    secure: bool = False

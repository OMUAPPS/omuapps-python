from dataclasses import dataclass


@dataclass(frozen=True)
class Address:
    host: str | None
    port: int
    secure: bool = False

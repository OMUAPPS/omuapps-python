from __future__ import annotations

from omu.identifier import Identifier
from pydantic import BaseModel


class Provider(BaseModel):
    id: Identifier
    url: str
    name: str
    version: str
    repository_url: str
    regex: str
    image_url: str | None = None

    def key(self) -> str:
        return self.id.key()

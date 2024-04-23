from __future__ import annotations

from pydantic import BaseModel


class Channel(BaseModel):
    provider_id: str
    id: str
    url: str
    name: str
    description: str
    active: bool
    icon_url: str

    def key(self) -> str:
        return f"{self.provider_id}:{self.url}"

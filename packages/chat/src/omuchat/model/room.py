from __future__ import annotations

from datetime import datetime
from typing import Literal, NotRequired, TypedDict

from omu.identifier import Identifier
from pydantic import BaseModel


class RoomMetadata(TypedDict):
    url: NotRequired[str]
    title: NotRequired[str]
    description: NotRequired[str]
    thumbnail: NotRequired[str]
    viewers: NotRequired[int]
    created_at: NotRequired[str]
    started_at: NotRequired[str]
    ended_at: NotRequired[str]


type Status = Literal["online", "reserved", "offline"]


class Room(BaseModel):
    id: Identifier
    provider_id: Identifier
    connected: bool
    status: Status
    metadata: RoomMetadata | None = None
    channel_id: str | None = None
    created_at: datetime | None = None

    def key(self) -> str:
        return self.id.key()

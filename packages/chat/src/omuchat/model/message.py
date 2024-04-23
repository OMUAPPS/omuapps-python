from __future__ import annotations

from datetime import datetime
from typing import Any, List

from omu.identifier import Identifier
from pydantic import BaseModel

from .gift import Gift
from .paid import Paid


class Message(BaseModel):
    room_id: str
    id: Identifier
    author_id: str | None = None
    content: Any | None = None
    paid: Paid | None = None
    gifts: List[Gift] | None = None
    created_at: datetime | None = None

    @property
    def text(self) -> str:
        if not self.content:
            return ""
        return str(self.content)

    def key(self) -> str:
        return self.id.key()

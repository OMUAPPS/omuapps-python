from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, NotRequired, TypedDict

from omu.helper import map_optional
from omu.identifier import Identifier
from omu.interface import Keyable
from omu.model import Model

from . import content
from .gift import Gift, GiftJson
from .paid import Paid, PaidJson


class MessageJson(TypedDict):
    room_id: str
    id: str
    author_id: NotRequired[str] | None
    content: NotRequired[content.ComponentJson] | None
    paid: NotRequired[PaidJson] | None
    gifts: NotRequired[List[GiftJson]] | None
    created_at: NotRequired[str] | None  # ISO 8601 date string


@dataclass
class Message(Keyable, Model[MessageJson]):
    room_id: str
    id: Identifier
    author_id: str | None = None
    content: content.Component | None = None
    paid: Paid | None = None
    gifts: List[Gift] | None = None
    created_at: datetime | None = None

    @classmethod
    def from_json(cls, json: MessageJson) -> Message:
        created_at = None
        if json.get("created_at") and json["created_at"]:
            created_at = datetime.fromisoformat(json["created_at"])

        return cls(
            room_id=json["room_id"],
            id=Identifier.from_key(json["id"]),
            author_id=json.get("author_id"),
            content=map_optional(json.get("content"), content.deserialize),
            paid=map_optional(json.get("paid"), Paid.from_json),
            gifts=map_optional(
                json.get("gifts"),
                lambda gifts: list(map(Gift.from_json, gifts)),
                [],
            ),
            created_at=created_at,
        )

    def to_json(self) -> MessageJson:
        return MessageJson(
            room_id=self.room_id,
            id=self.id.key(),
            author_id=self.author_id,
            content=content.serialize(self.content) if self.content else None,
            paid=self.paid.to_json() if self.paid else None,
            gifts=[gift.to_json() for gift in self.gifts] if self.gifts else None,
            created_at=self.created_at.isoformat() if self.created_at else None,
        )

    @property
    def text(self) -> str:
        if not self.content:
            return ""
        return str(self.content)

    def key(self) -> str:
        return self.id.key()

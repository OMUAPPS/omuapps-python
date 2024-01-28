from __future__ import annotations

from datetime import datetime
from typing import List, NotRequired, TypedDict

from omu.interface import Keyable, Model

from .content import ContentComponent, ContentJson, ImageContent, TextContent
from .gift import Gift, GiftJson
from .paid import Paid, PaidJson


class MessageJson(TypedDict):
    room_id: str
    id: str
    author_id: NotRequired[str] | None
    content: NotRequired[ContentJson] | None
    paid: NotRequired[PaidJson] | None
    gifts: NotRequired[List[GiftJson]] | None
    created_at: NotRequired[str] | None  # ISO 8601 date string


class Message(Keyable, Model[MessageJson]):
    def __init__(
        self,
        room_id: str,
        id: str,
        author_id: str | None = None,
        content: ContentComponent | None = None,
        paid: Paid | None = None,
        gifts: List[Gift] | None = None,
        created_at: datetime | None = None,
    ) -> None:
        if created_at and not isinstance(created_at, datetime):
            raise TypeError(f"created_at must be datetime, not {type(created_at)}")
        self.room_id = room_id
        self.id = id
        self.content = content
        self.author_id = author_id
        self.paid = paid
        self.gifts = gifts
        self.created_at = created_at

    @classmethod
    def from_json(cls, json: MessageJson) -> "Message":
        content = None
        if json.get("content", None) and json["content"]:
            content = ContentComponent.from_json(json["content"])
        paid = None
        if json.get("paid", None) and json["paid"]:
            paid = Paid.from_json(json["paid"])
        gifts = []
        if json.get("gifts", None) and json["gifts"]:
            gifts = [Gift.from_json(gift) for gift in json["gifts"]]
        created_at = None
        if json.get("created_at", None) and json["created_at"]:
            created_at = datetime.fromisoformat(json["created_at"])

        return cls(
            room_id=json["room_id"],
            id=json["id"],
            author_id=json.get("author_id"),
            content=content,
            paid=paid,
            gifts=gifts,
            created_at=created_at,
        )

    @property
    def text(self) -> str:
        if not self.content:
            return ""
        parts = []
        components: List[ContentComponent] = [self.content]
        while components:
            component = components.pop(0)
            if isinstance(component, TextContent):
                parts.append(component.text)
            elif isinstance(component, ImageContent):
                parts.append(f":{component.id}:")
            if component.siblings:
                components.extend(component.siblings)
        return "".join(parts)

    def key(self) -> str:
        return f"{self.room_id}#{self.id}"

    def to_json(self) -> MessageJson:
        return MessageJson(
            room_id=self.room_id,
            id=self.id,
            author_id=self.author_id,
            content=self.content.to_json() if self.content else None,
            paid=self.paid.to_json() if self.paid else None,
            gifts=[gift.to_json() for gift in self.gifts] if self.gifts else None,
            created_at=self.created_at.isoformat() if self.created_at else None,
        )

    def __str__(self) -> str:
        return f"Message({self.room_id}, {self.id}, {self.author_id}, {self.content}, {self.paid}, {self.gifts}, {self.created_at})"

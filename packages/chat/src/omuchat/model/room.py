from typing import Literal, NotRequired, TypedDict, Hashable

from omu.interface import Keyable
from omu.extension.table import Model
from omu.helper import map_optional

from datetime import datetime


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


class RoomJson(TypedDict):
    id: str
    provider_id: str
    connected: bool
    status: Status
    metadata: NotRequired[RoomMetadata] | None
    channel_id: NotRequired[str] | None
    created_at: NotRequired[str] | None  # ISO 8601 date string


class Room(Keyable, Model[RoomJson], Hashable):
    def __init__(
        self,
        *,
        id: str,
        provider_id: str,
        connected: bool,
        status: Status,
        metadata: RoomMetadata | None = None,
        channel_id: str | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self.id = id
        self.provider_id = provider_id
        self.connected = connected
        self.status: Status = status
        self.metadata = metadata
        self.channel_id = channel_id
        self.created_at = created_at

    @staticmethod
    def from_json(json: RoomJson) -> "Room":
        return Room(
            id=json["id"],
            provider_id=json["provider_id"],
            connected=json["connected"],
            status=json["status"],
            metadata=json.get("metadata"),
            channel_id=json.get("channel_id"),
            created_at=map_optional(json.get("created_at"), datetime.fromisoformat),
        )

    def to_json(self) -> RoomJson:
        return RoomJson(
            id=self.id,
            provider_id=self.provider_id,
            connected=self.connected,
            status=self.status,
            metadata=self.metadata,
            channel_id=self.channel_id,
            created_at=map_optional(self.created_at, datetime.isoformat),
        )

    def key(self) -> str:
        return f"{self.id}@{self.provider_id}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Room):
            return NotImplemented
        return self.key() == other.key()

    def __hash__(self) -> int:
        return hash(self.key())
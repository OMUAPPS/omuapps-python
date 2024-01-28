from typing import NotRequired, TypedDict

from omu.interface import Keyable, Model


class RoomJson(TypedDict):
    id: str
    provider_id: str
    channel_id: NotRequired[str] | None
    name: str
    description: NotRequired[str] | None
    online: bool
    url: str
    image_url: NotRequired[str] | None
    viewers: NotRequired[int] | None


class Room(Keyable, Model[RoomJson]):
    def __init__(
        self,
        id: str,
        provider_id: str,
        name: str,
        online: bool,
        url: str,
        channel_id: str | None = None,
        description: str | None = None,
        image_url: str | None = None,
        viewers: int | None = None,
    ) -> None:
        self.id = id
        self.provider_id = provider_id
        self.channel_id = channel_id
        self.name = name
        self.description = description
        self.online = online
        self.url = url
        self.image_url = image_url
        self.viewers = viewers

    @classmethod
    def from_json(cls, json: RoomJson) -> "Room":
        return cls(
            id=json["id"],
            provider_id=json["provider_id"],
            channel_id=json.get("channel_id", None),
            name=json["name"],
            description=json.get("description", None),
            online=json["online"],
            url=json["url"],
            image_url=json.get("image_url", None),
            viewers=json.get("viewers", None),
        )

    def key(self) -> str:
        return f"{self.id}@{self.provider_id}"

    def to_json(self) -> RoomJson:
        return RoomJson(
            id=self.id,
            provider_id=self.provider_id,
            channel_id=self.channel_id,
            name=self.name,
            description=self.description,
            online=self.online,
            url=self.url,
            image_url=self.image_url,
            viewers=self.viewers,
        )

    def __str__(self) -> str:
        return self.name

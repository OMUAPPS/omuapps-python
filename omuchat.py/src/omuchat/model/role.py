from typing import NotRequired, TypedDict

from omu.interface import Keyable, Model


class RoleJson(TypedDict):
    id: str
    name: str
    is_owner: bool
    is_moderator: bool
    icon_url: NotRequired[str] | None
    color: NotRequired[str] | None


class Role(Keyable, Model[RoleJson]):
    def __init__(
        self,
        id: str,
        name: str,
        is_owner: bool,
        is_moderator: bool,
        icon_url: str | None = None,
        color: str | None = None,
    ) -> None:
        self.id = id
        self.name = name
        self.is_owner = is_owner
        self.is_moderator = is_moderator
        self.icon_url = icon_url
        self.color = color

    def key(self) -> str:
        return self.id

    def to_json(self) -> RoleJson:
        return {
            "id": self.id,
            "name": self.name,
            "is_owner": self.is_owner,
            "is_moderator": self.is_moderator,
            "icon_url": self.icon_url,
            "color": self.color,
        }

    @classmethod
    def from_json(cls, json: RoleJson) -> "Role":
        return cls(
            id=json["id"],
            name=json["name"],
            is_owner=json["is_owner"],
            is_moderator=json["is_moderator"],
            icon_url=json["icon_url"],
            color=json["color"],
        )

    def __str__(self) -> str:
        return self.name


MODERATOR = Role(
    id="moderator",
    name="Moderator",
    is_owner=False,
    is_moderator=True,
    icon_url=None,
    color=None,
)
OWNER = Role(
    id="owner",
    name="Owner",
    is_owner=True,
    is_moderator=True,
    icon_url=None,
    color=None,
)

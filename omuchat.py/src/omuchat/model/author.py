from typing import List, NotRequired, TypedDict

from omu.interface import Keyable, Model

from .role import Role, RoleJson


class AuthorJson(TypedDict):
    provider_id: str
    id: str
    name: str
    avatar_url: NotRequired[str] | None
    roles: NotRequired[List[RoleJson]] | None


class Author(Keyable, Model[AuthorJson]):
    def __init__(
        self,
        provider_id: str,
        id: str,
        name: str,
        avatar_url: str | None,
        roles: List[Role] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.id = id
        self.name = name
        self.avatar_url = avatar_url
        self.roles = roles or []

    def key(self) -> str:
        return f"{self.provider_id}:{self.id}"

    def to_json(self) -> AuthorJson:
        return {
            "provider_id": self.provider_id,
            "id": self.id,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "roles": [role.to_json() for role in self.roles],
        }

    @classmethod
    def from_json(cls, json: AuthorJson) -> "Author":
        return cls(
            provider_id=json["provider_id"],
            id=json["id"],
            name=json["name"],
            avatar_url=json.get("avatar_url", None) and json["avatar_url"],
            roles=[Role.from_json(role) for role in json.get("roles", []) or []],
        )

    def __str__(self) -> str:
        return f"Author(id={self.id}, name={self.name}, avatar_url={self.avatar_url}, roles={self.roles})"

from __future__ import annotations

from typing import List, NotRequired, TypedDict

from omu.helper import map_optional
from omu.interface import Keyable
from omu.model import Model

from .role import Role, RoleJson


class AuthorJson(TypedDict):
    provider_id: str
    id: str
    name: str
    screen_id: NotRequired[str] | None
    avatar_url: NotRequired[str] | None
    roles: NotRequired[List[RoleJson]] | None


class Author(Keyable, Model[AuthorJson]):
    def __init__(
        self,
        *,
        provider_id: str,
        id: str,
        name: str,
        screen_id: str | None = None,
        avatar_url: str | None = None,
        roles: List[Role] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.id = id
        self.name = name
        self.screen_id = screen_id
        self.avatar_url = avatar_url
        self.roles = roles or []

    def to_json(self) -> AuthorJson:
        return {
            "provider_id": self.provider_id,
            "id": self.id,
            "name": self.name,
            "screen_id": self.screen_id,
            "avatar_url": self.avatar_url,
            "roles": [role.to_json() for role in self.roles],
        }

    @classmethod
    def from_json(cls, json: AuthorJson) -> Author:
        return cls(
            provider_id=json["provider_id"],
            id=json["id"],
            name=json["name"],
            screen_id=json.get("screen_id"),
            avatar_url=json.get("avatar_url"),
            roles=map_optional(
                json.get("roles"),
                lambda roles: list(map(Role.from_json, roles)),
                [],
            ),
        )

    def key(self) -> str:
        return f"{self.provider_id}:{self.id}"

    def __str__(self) -> str:
        return f"Author(id={self.id}, name={self.name})"

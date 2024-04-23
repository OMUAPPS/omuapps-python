from typing import List, NotRequired, TypedDict

from pydantic import BaseModel, ConfigDict, Field

from .role import Role


class AuthorMetadata(TypedDict):
    url: NotRequired[str | None]
    screen_id: NotRequired[str | None]
    avatar_url: NotRequired[str | None]
    description: NotRequired[str | None]
    links: NotRequired[List[str] | None]


class Author(BaseModel):
    provider_id: str
    id: str
    name: str | None = None
    avatar_url: str | None = None
    roles: list[Role] = Field(default_factory=list)
    metadata: AuthorMetadata | None = None
    model_config = ConfigDict(arbitrary_types_allowed=True)

    def key(self) -> str:
        return f"{self.provider_id}:{self.id}"

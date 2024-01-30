from __future__ import annotations

from typing import NotRequired, TypedDict

from omu.interface import Keyable, Model


class EndpointInfoJson(TypedDict):
    owner: str
    name: str
    description: NotRequired[str] | None


class EndpointInfo(Keyable, Model[EndpointInfoJson]):
    def __init__(
        self,
        owner: str,
        name: str,
        description: str | None = None,
    ) -> None:
        self.owner = owner
        self.name = name
        self.description = description

    @classmethod
    def from_json(cls, json: EndpointInfoJson) -> EndpointInfo:
        return EndpointInfo(**json)

    def to_json(self) -> EndpointInfoJson:
        return EndpointInfoJson(
            owner=self.owner,
            name=self.name,
            description=self.description,
        )

    def key(self) -> str:
        return f"{self.owner}:{self.name}"

    def __str__(self) -> str:
        return f"EndpointInfo({self.key()})"

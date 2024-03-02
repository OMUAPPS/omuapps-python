from __future__ import annotations

from typing import TypedDict

from omu.extension.table import Model
from omu.identifier import Identifier
from omu.interface import Keyable


class EndpointInfoJson(TypedDict):
    identifier: str
    description: str


class EndpointInfo(Keyable, Model[EndpointInfoJson]):
    def __init__(
        self,
        identifier: Identifier,
        description: str = "",
    ) -> None:
        self.identifier = identifier
        self.description = description

    @classmethod
    def from_json(cls, json: EndpointInfoJson) -> EndpointInfo:
        return EndpointInfo(
            identifier=Identifier.from_key(json["identifier"]),
            description=json.get("description", ""),
        )

    def to_json(self) -> EndpointInfoJson:
        return EndpointInfoJson(
            identifier=self.identifier.key(),
            description=self.description,
        )

    def key(self) -> str:
        return self.identifier.key()

    def __str__(self) -> str:
        return f"EndpointInfo(identifier={self.identifier}, description={self.description})"

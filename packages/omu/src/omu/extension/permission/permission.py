from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from omu.identifier import Identifier
from omu.model import Model


class PermissionJson(TypedDict):
    identifier: str


@dataclass(frozen=True)
class PermissionType(Model[PermissionJson]):
    identifier: Identifier

    @classmethod
    def create(
        cls,
        identifier: Identifier,
        name: str,
    ) -> PermissionType:
        return PermissionType(
            identifier=identifier / name,
        )

    def to_json(self) -> PermissionJson:
        return {
            "identifier": self.identifier.key(),
        }

    @classmethod
    def from_json(cls, json: PermissionJson) -> PermissionType:
        return PermissionType(
            identifier=Identifier(json["identifier"]),
        )

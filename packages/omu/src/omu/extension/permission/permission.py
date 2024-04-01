from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from omu.identifier import Identifier
from omu.model import Model


class PermissionTypeJson(TypedDict):
    identifier: str


@dataclass(frozen=True)
class PermissionType(Model[PermissionTypeJson]):
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

    def to_json(self) -> PermissionTypeJson:
        return {
            "identifier": self.identifier.key(),
        }

    @classmethod
    def from_json(cls, json: PermissionTypeJson) -> PermissionType:
        return PermissionType(
            identifier=Identifier(json["identifier"]),
        )

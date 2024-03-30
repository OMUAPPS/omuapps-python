from __future__ import annotations

from dataclasses import dataclass

from omu import Identifier
from omu.model import Model


@dataclass(frozen=True)
class PermissionType(Model[dict]):
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

    def to_json(self) -> dict:
        return {
            "identifier": self.identifier.key(),
        }

    @classmethod
    def from_json(cls, json: dict) -> PermissionType:
        return PermissionType(
            identifier=Identifier(json["identifier"]),
        )

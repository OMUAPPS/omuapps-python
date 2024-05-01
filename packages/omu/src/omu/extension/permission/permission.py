from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

from omu.identifier import Identifier
from omu.localization import LocalizedText
from omu.model import Model

type PermissionLevel = Literal["low", "medium", "high"]


class PermissionMetadata(TypedDict):
    name: LocalizedText
    note: LocalizedText
    level: PermissionLevel


class PermissionTypeJson(TypedDict):
    id: str
    metadata: PermissionMetadata


@dataclass(frozen=True)
class PermissionType(Model[PermissionTypeJson]):
    id: Identifier
    metadata: PermissionMetadata

    @classmethod
    def create(
        cls,
        identifier: Identifier,
        name: str,
        metadata: PermissionMetadata,
    ) -> PermissionType:
        return PermissionType(
            id=identifier / name,
            metadata=metadata,
        )

    def to_json(self) -> PermissionTypeJson:
        return {
            "id": self.id.key(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, json: PermissionTypeJson) -> PermissionType:
        return PermissionType(
            id=Identifier.from_key(json["id"]),
            metadata=json["metadata"],
        )


NO_PERMISSION_ID = Identifier("omu", "no_permission")
NO_PERMISSION = PermissionType.create(
    NO_PERMISSION_ID,
    "No Permission",
    {
        "name": {
            "en": "No Permission",
            "ja": "権限なし",
        },
        "note": {
            "en": "No permission required.",
            "ja": "権限は必要ありません。",
        },
        "level": "low",
    },
)
GENERAL_PERMISSION_ID = Identifier("omu", "general_permission")
GENERAL_PERMISSION = PermissionType.create(
    GENERAL_PERMISSION_ID,
    "General Permission",
    {
        "name": {
            "en": "General Permission",
            "ja": "一般権限",
        },
        "note": {
            "en": "General permission required.",
            "ja": "一般権限が必要です。",
        },
        "level": "medium",
    },
)

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

from omu.extension.extension import ExtensionType
from omu.identifier import Identifier


@dataclass(frozen=True)
class PermissionType(BaseModel):
    identifier: Identifier

    @classmethod
    def create(
        cls,
        identifier: Identifier | ExtensionType,
        name: str,
    ) -> PermissionType:
        return PermissionType(
            identifier=identifier / name,
        )

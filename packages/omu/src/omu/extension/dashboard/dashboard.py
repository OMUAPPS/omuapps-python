from __future__ import annotations

from dataclasses import dataclass
from typing import List, TypedDict

from omu.app import App, AppJson
from omu.extension.permission.permission import PermissionType, PermissionTypeJson
from omu.model import Model


class PermissionRequestJson(TypedDict):
    request_id: int
    app: AppJson
    permissions: List[PermissionTypeJson]


@dataclass(frozen=True)
class PermissionRequest(Model[PermissionRequestJson]):
    request_id: int
    app: App
    permissions: List[PermissionType]

    @classmethod
    def from_json(cls, json: PermissionRequestJson) -> PermissionRequest:
        return cls(
            request_id=json["request_id"],
            app=App.from_json(json["app"]),
            permissions=[PermissionType.from_json(p) for p in json["permissions"]],
        )

    def to_json(self) -> PermissionRequestJson:
        return {
            "request_id": self.request_id,
            "app": self.app.to_json(),
            "permissions": [p.to_json() for p in self.permissions],
        }

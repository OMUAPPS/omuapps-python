from __future__ import annotations

from dataclasses import dataclass
from typing import List, TypedDict

from pydantic import BaseModel

from omu.app import App
from omu.extension.permission.permission import PermissionType


@dataclass(frozen=True)
class PermissionRequest(BaseModel):
    request_id: str
    app: App
    permissions: List[PermissionType]


class DashboardOpenAppResponse(TypedDict):
    success: bool
    already_open: bool
    dashboard_not_connected: bool

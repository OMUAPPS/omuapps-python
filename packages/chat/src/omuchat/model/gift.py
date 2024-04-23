from __future__ import annotations

from pydantic import BaseModel


class Gift(BaseModel):
    id: str
    name: str | None = None
    amount: int | None = None
    is_paid: bool | None = None
    image_url: str | None = None

from __future__ import annotations

from pydantic import BaseModel


class Paid(BaseModel):
    amount: float
    currency: str

from typing import TypedDict

from omu.interface import Model


class PaidJson(TypedDict):
    amount: float
    currency: str


class Paid(Model[PaidJson]):
    def __init__(self, amount: float, currency: str) -> None:
        self.amount = amount
        self.currency = currency

    @classmethod
    def from_json(cls, json: PaidJson) -> "Paid":
        return cls(amount=json["amount"], currency=json["currency"])

    def to_json(self) -> PaidJson:
        return {"amount": self.amount, "currency": self.currency}

    def __str__(self) -> str:
        return f"{self.amount} {self.currency}"

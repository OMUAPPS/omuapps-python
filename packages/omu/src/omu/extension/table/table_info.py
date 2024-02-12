from __future__ import annotations

from typing import NotRequired, TypedDict

from omu.identifier import Identifier
from omu.interface import Keyable, Model


class TableInfoJson(TypedDict):
    identifier: str
    cache_size: NotRequired[int] | None


class TableInfo(Keyable, Model):
    def __init__(
        self,
        identifier: Identifier,
        cache_size: int | None = None,
    ) -> None:
        self.identifier = identifier
        self.cache_size = cache_size

    @classmethod
    def from_json(cls, json: TableInfoJson) -> TableInfo:
        return TableInfo(
            identifier=Identifier.from_key(json["identifier"]),
            cache_size=json.get("cache_size"),
        )

    @classmethod
    def of(
        cls,
        identifier: Identifier,
        cache_size: int | None = None,
    ) -> TableInfo:
        return TableInfo(
            identifier=identifier,
            cache_size=cache_size,
        )

    def key(self) -> str:
        return self.identifier.key()

    def to_json(self) -> TableInfoJson:
        return TableInfoJson(
            identifier=self.identifier.key(),
            cache_size=self.cache_size,
        )

    def __str__(self) -> str:
        return f"TableInfo({self.identifier}, {self.cache_size})"

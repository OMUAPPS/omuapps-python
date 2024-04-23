from __future__ import annotations

from typing import Final, List, NotRequired, TypedDict

from pydantic import BaseModel

from omu.identifier import Identifier
from omu.localization import LocalizedText
from omu.localization.locale import Locale


class AppMetadata(TypedDict):
    locale: Locale
    name: NotRequired[LocalizedText]
    description: NotRequired[LocalizedText]
    image: NotRequired[LocalizedText]
    site: NotRequired[LocalizedText]
    repository: NotRequired[LocalizedText]
    authors: NotRequired[LocalizedText]
    license: NotRequired[LocalizedText]
    tags: NotRequired[List[str]]


class App(BaseModel):
    identifier: Final[Identifier]
    version: str | None = None
    url: str | None = None
    metadata: AppMetadata | None = None

    def key(self) -> str:
        return self.identifier.key()

    def __hash__(self) -> int:
        return hash(self.key())

    def __repr__(self) -> str:
        return f"App({self.key()})"

from __future__ import annotations

from typing import Final, NotRequired, TypedDict

from omu.identifier import Identifier
from omu.interface import Keyable
from omu.localization import LocalizedText
from omu.localization.locale import Locale
from omu.model import Model


class AppLocalization(TypedDict):
    locale: Locale
    name: NotRequired[LocalizedText]
    description: NotRequired[LocalizedText]
    image: NotRequired[LocalizedText]
    site: NotRequired[LocalizedText]
    repository: NotRequired[LocalizedText]
    authors: NotRequired[LocalizedText]
    license: NotRequired[LocalizedText]


class AppJson(TypedDict):
    identifier: str
    version: NotRequired[str] | None
    url: NotRequired[str] | None
    localizations: NotRequired[AppLocalization] | None


class App(Keyable, Model[AppJson]):
    def __init__(
        self,
        identifier: Identifier | str,
        *,
        version: str | None = None,
        url: str | None = None,
        localizations: AppLocalization | None = None,
    ) -> None:
        if isinstance(identifier, str):
            identifier = Identifier.from_key(identifier)
        self.identifier: Final[Identifier] = identifier
        self.version = version
        self.url = url
        self.localizations = localizations

    @classmethod
    def from_json(cls, json: AppJson) -> App:
        identifier = Identifier.from_key(json["identifier"])
        return cls(
            identifier,
            version=json.get("version"),
            url=json.get("url"),
            localizations=json.get("localizations"),
        )

    def to_json(self) -> AppJson:
        return AppJson(
            identifier=self.key(),
            version=self.version,
            url=self.url,
            localizations=self.localizations,
        )

    def key(self) -> str:
        return self.identifier.key()

    def __hash__(self) -> int:
        return hash(self.key())

    def __repr__(self) -> str:
        return f"App({self.key()})"

from __future__ import annotations

from typing import Final, List, NotRequired, TypedDict

from omu.identifier import Identifier
from omu.interface import Keyable
from omu.model import Model


class AppJson(TypedDict):
    identifier: str
    version: NotRequired[str] | None
    license: NotRequired[str] | None
    description: NotRequired[str] | None
    authors: NotRequired[List[str]] | None
    site_url: NotRequired[str] | None
    repository_url: NotRequired[str] | None
    image_url: NotRequired[str] | None


class App(Keyable, Model[AppJson]):
    def __init__(
        self,
        identifier: Identifier | str,
        *,
        version: str | None = None,
        license: str | None = None,
        description: str | None = None,
        authors: List[str] | None = None,
        site_url: str | None = None,
        repository_url: str | None = None,
        image_url: str | None = None,
    ) -> None:
        if isinstance(identifier, str):
            identifier = Identifier.from_key(identifier)
        self.identifier: Final[Identifier] = identifier
        self.name: Final[str] = "/".join(identifier.path)
        self.group: Final[str] = identifier.namespace
        self.version = version
        self.license = license
        self.description = description
        self.authors = authors
        self.site_url = site_url
        self.repository_url = repository_url
        self.image_url = image_url

    @classmethod
    def from_json(cls, json: AppJson) -> App:
        identifier = Identifier.from_key(json["identifier"])
        return cls(
            identifier,
            version=json.get("version"),
            license=json.get("license"),
            description=json.get("description"),
            authors=json.get("authors"),
            site_url=json.get("site_url"),
            repository_url=json.get("repository_url"),
            image_url=json.get("image_url"),
        )

    def to_json(self) -> AppJson:
        return AppJson(
            identifier=self.key(),
            version=self.version,
            license=self.license,
            description=self.description,
            authors=self.authors,
            site_url=self.site_url,
            repository_url=self.repository_url,
            image_url=self.image_url,
        )

    def key(self) -> str:
        return self.identifier.key()

    def __hash__(self) -> int:
        return hash(self.key())

    def __repr__(self) -> str:
        return f"App({self.key()})"

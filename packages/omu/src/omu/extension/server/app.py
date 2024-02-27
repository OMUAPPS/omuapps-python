from __future__ import annotations

from typing import List, NotRequired, TypedDict

from omu.identifier import Identifier
from omu.interface import Keyable, Model


class AppJson(TypedDict):
    identifier: str
    version: str
    license: NotRequired[str]
    description: NotRequired[str]
    authors: NotRequired[List[str]]
    site_url: NotRequired[str]
    repository_url: NotRequired[str]
    image_url: NotRequired[str]


class App(Keyable, Model[AppJson]):
    def __init__(
        self,
        *,
        name: str,
        group: str,
        version: str | None = None,
        license: str | None = None,
        description: str | None = None,
        authors: List[str] | None = None,
        site_url: str | None = None,
        repository_url: str | None = None,
        image_url: str | None = None,
    ) -> None:
        self.name = name
        self.group = group
        self.version = version
        self.license = license
        self.description = description
        self.authors = authors
        self.site_url = site_url
        self.repository_url = repository_url
        self.image_url = image_url

    @classmethod
    def from_identifier(
        cls,
        identifier: Identifier,
        *,
        version: str | None = None,
        license: str | None = None,
        description: str | None = None,
        authors: List[str] | None = None,
        site_url: str | None = None,
        repository_url: str | None = None,
        image_url: str | None = None,
    ) -> App:
        return cls(
            name=identifier.name,
            group=identifier.namespace,
            version=version,
            license=license,
            description=description,
            authors=authors,
            site_url=site_url,
            repository_url=repository_url,
            image_url=image_url,
        )

    @classmethod
    def from_json(cls, json: AppJson) -> App:
        identifier = Identifier.from_key(json["identifier"])
        return cls(
            name=identifier.name,
            group=identifier.namespace,
            version=json.get("version"),
            license=json.get("license"),
            description=json.get("description"),
            authors=json.get("authors"),
            site_url=json.get("site_url"),
            repository_url=json.get("repository_url"),
            image_url=json.get("image_url"),
        )

    def to_json(self) -> AppJson:
        return {
            "identifier": self.key(),
            "version": self.version,
            "license": self.license,
            "description": self.description,
            "authors": self.authors,
            "site_url": self.site_url,
            "repository_url": self.repository_url,
            "image_url": self.image_url,
        }

    def key(self) -> str:
        return Identifier.format(self.group, self.name)

    def __hash__(self) -> int:
        return hash(self.key())

    def __repr__(self) -> str:
        return f"App({self.key()})"

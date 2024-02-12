from __future__ import annotations

from typing import List, NotRequired, TypedDict

from omu.interface import Keyable, Model


class AppJson(TypedDict):
    name: str
    group: str
    version: str
    description: NotRequired[str] | None
    authors: NotRequired[List[str]] | None
    site_url: NotRequired[str] | None
    repository_url: NotRequired[str] | None
    license: NotRequired[str] | None
    image_url: NotRequired[str] | None


class App(Keyable, Model[AppJson]):
    def __init__(
        self,
        name: str,
        group: str,
        version: str,
        description: str | None = None,
        authors: List[str] | None = None,
        site_url: str | None = None,
        repository_url: str | None = None,
        license: str | None = None,
        image_url: str | None = None,
    ) -> None:
        self.name = name
        self.group = group
        self.version = version
        self.description = description
        self.authors = authors
        self.site_url = site_url
        self.repository_url = repository_url
        self.license = license
        self.image_url = image_url

    @classmethod
    def from_json(cls, json: AppJson) -> App:
        return App(**json)

    def key(self) -> str:
        return f"{self.group}/{self.name}"

    def to_json(self) -> AppJson:
        return {
            "name": self.name,
            "group": self.group,
            "version": self.version,
            "description": self.description,
            "authors": self.authors,
            "site_url": self.site_url,
            "repository_url": self.repository_url,
            "license": self.license,
            "image_url": self.image_url,
        }

    def __str__(self) -> str:
        return f"{self.group}/{self.name} v{self.version}"

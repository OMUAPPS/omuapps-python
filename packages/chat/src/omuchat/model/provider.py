from __future__ import annotations

from typing import TypedDict

from omu.interface import Keyable
from omu.model import Model


class ProviderJson(TypedDict):
    id: str
    url: str
    name: str
    version: str
    repository_url: str
    image_url: str | None
    description: str
    regex: str


class Provider(Keyable, Model[ProviderJson]):
    def __init__(
        self,
        *,
        id: str,
        url: str,
        name: str,
        version: str,
        repository_url: str,
        description: str,
        regex: str,
        image_url: str | None = None,
    ) -> None:
        self.id = id
        self.url = url
        self.name = name
        self.version = version
        self.repository_url = repository_url
        self.image_url = image_url
        self.description = description
        self.regex = regex

    @classmethod
    def from_json(cls, json: ProviderJson) -> Provider:
        return cls(
            id=json["id"],
            url=json["url"],
            name=json["name"],
            version=json["version"],
            repository_url=json["repository_url"],
            image_url=json["image_url"],
            description=json["description"],
            regex=json["regex"],
        )

    def to_json(self) -> ProviderJson:
        return ProviderJson(
            id=self.id,
            url=self.url,
            name=self.name,
            version=self.version,
            repository_url=self.repository_url,
            image_url=self.image_url,
            description=self.description,
            regex=self.regex,
        )

    def key(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"Provider({self.key()})"

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, TypedDict

from omu import Identifier
from omu.model import Model


class PluginMetadata(TypedDict):
    dependencies: Mapping[str, str | None]
    module: str


class PluginJson(TypedDict):
    identifier: str
    metadata: PluginMetadata


@dataclass(frozen=True)
class PluginType(Model[PluginJson]):
    identifier: Identifier
    metadata: PluginMetadata

    @classmethod
    def create(
        cls,
        identifier: Identifier,
        name: str,
        metadata: PluginMetadata,
    ) -> PluginType:
        return PluginType(
            identifier=identifier / name,
            metadata=metadata,
        )

    def to_json(self) -> PluginJson:
        return {
            "identifier": self.identifier.key(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, json: PluginJson) -> PluginType:
        return PluginType(
            identifier=Identifier(json["identifier"]),
            metadata=json["metadata"],
        )

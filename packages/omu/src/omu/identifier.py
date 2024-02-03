from __future__ import annotations

from .interface import Keyable


class Identifier(Keyable):
    def __init__(self, namespace: str, name: str) -> None:
        self.namespace = namespace
        self.name = name

    @classmethod
    def create(cls, namespace: str, name: str) -> Identifier:
        return cls(namespace, name)

    @classmethod
    def from_key(cls, key: str) -> Identifier:
        namespace, name = key.split(":")
        if not namespace or not name:
            raise Exception(f"Invalid key {key}")
        return cls(namespace, name)

    def key(self) -> str:
        return f"{self.namespace}:{self.name}"

from __future__ import annotations

import re

from .interface import Keyable

NAMESPACE_REGEX = re.compile(r"^\w+([\./:][\w]+)*$")
NAME_REGEX = re.compile(r"^[\w-]+$")


class Identifier(Keyable):
    def __init__(self, namespace: str, name: str) -> None:
        self.validate(namespace, name)
        self.namespace = namespace
        self.name = name

    @classmethod
    def validate(cls, namespace: str, name: str) -> None:
        if not NAMESPACE_REGEX.match(namespace):
            raise Exception(f"Invalid namespace {namespace}")
        if not NAME_REGEX.match(name):
            raise Exception(f"Invalid name {name}")

    @classmethod
    def format(cls, namespace: str, name: str) -> str:
        cls.validate(namespace, name)
        return f"{namespace}:{name}"

    @classmethod
    def create(cls, namespace: str, name: str) -> Identifier:
        return cls(namespace, name)

    @classmethod
    def from_key(cls, key: str) -> Identifier:
        separator = key.rfind(":")
        if separator == -1:
            raise Exception(f"Invalid key {key}")
        namespace, name = key[:separator], key[separator + 1 :]
        if not namespace or not name:
            raise Exception(f"Invalid key {key}")
        cls.validate(namespace, name)
        return cls(namespace, name)

    def key(self) -> str:
        return f"{self.namespace}:{self.name}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Identifier):
            return NotImplemented
        return self.namespace == other.namespace and self.name == other.name

    def __hash__(self) -> int:
        return hash((self.namespace, self.name))

    def __repr__(self) -> str:
        return f"Identifier({self.namespace!r}, {self.name!r})"

    def __str__(self) -> str:
        return self.key()

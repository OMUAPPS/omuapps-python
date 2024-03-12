from __future__ import annotations

import re
from pathlib import Path

from omu.helper import generate_md5_hash, sanitize_filename

from .interface import Keyable

NAMESPACE_REGEX = re.compile(r"^(\.[^.]|[\w-])+$")
NAME_REGEX = re.compile(r"^[\w-]+$")


class Identifier(Keyable):
    def __init__(self, namespace: str, *path: str) -> None:
        self.validate(namespace, *path)
        self.namespace = namespace
        self.path = path
        self.name = path[-1]

    @classmethod
    def validate(cls, namespace: str, *path: str) -> None:
        if not NAMESPACE_REGEX.match(namespace):
            raise Exception(f"Invalid namespace {namespace}")
        for name in path:
            if not NAME_REGEX.match(name):
                raise Exception(f"Invalid name {name}")

    @classmethod
    def format(cls, namespace: str, *path: str) -> str:
        cls.validate(namespace, *path)
        return f"{namespace}:{'/'.join(path)}"

    @classmethod
    def from_key(cls, key: str) -> Identifier:
        separator = key.rfind(":")
        if separator == -1:
            raise Exception(f"Invalid key {key}")
        namespace, path = key[:separator], key[separator + 1 :]
        if not namespace or not path:
            raise Exception(f"Invalid key {key}")
        return cls(namespace, *path.split("/"))

    def key(self) -> str:
        return self.format(self.namespace, *self.path)

    def to_path(self) -> Path:
        namespace = (
            f"{sanitize_filename(self.namespace)}-{generate_md5_hash(self.namespace)}"
        )
        return Path(namespace, *self.path)

    def join(self, *path: str) -> Identifier:
        return Identifier(self.namespace, *self.path, *path)

    def __truediv__(self, name: str) -> Identifier:
        return self.join(name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Identifier):
            return NotImplemented
        return self.key() == other.key()

    def __hash__(self) -> int:
        return hash(self.key())

    def __repr__(self) -> str:
        return f"Identifier({self.key()})"

    def __str__(self) -> str:
        return self.key()

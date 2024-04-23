from __future__ import annotations

import re
import urllib.parse
from pathlib import Path
from typing import Final, Tuple

from pydantic import (
    BaseModel,
    field_validator,
)

from omu.helper import generate_md5_hash, sanitize_filename

NAMESPACE_REGEX = re.compile(r"^(\.[^/:.]|[\w-])+$")
NAME_REGEX = re.compile(r"^[^/:.]+$")


class Identifier(BaseModel):
    namespace: Final[str]
    path: Tuple[str, ...]

    def key(self) -> str:
        return f"{self.namespace}:{'/'.join(self.path)}"

    @field_validator("namespace")
    def validate_namespace(cls, value: str) -> str:
        if not NAMESPACE_REGEX.match(value):
            raise ValueError(
                f"Invalid namespace: Namespace must match {NAMESPACE_REGEX.pattern}"
            )
        return value

    @field_validator("path")
    def validate_path(cls, value: Tuple[str, ...]) -> Tuple[str, ...]:
        if not value:
            raise ValueError("Invalid path: Path must have at least one name")
        for name in value:
            if not NAME_REGEX.match(name):
                raise ValueError(f"Invalid name: Name must match {NAME_REGEX.pattern}")
        return value

    @classmethod
    def from_key(cls, key: str) -> Identifier:
        separator = key.find(":")
        if separator == -1:
            raise Exception(f"Invalid key: No separator found in {key}")
        if key.find(":", separator + 1) != -1:
            raise Exception(f"Invalid key: Multiple separators found in {key}")
        namespace, path = key[:separator], key[separator + 1 :]
        if not namespace or not path:
            raise Exception("Invalid key: Namespace and path cannot be empty")
        return cls(namespace=namespace, path=tuple(path.split("/")))

    @classmethod
    def from_url(cls, url: str) -> Identifier:
        parsed = urllib.parse.urlparse(url)
        namespace = cls.namespace_from_url(url)
        path = parsed.path.split("/")[1:]
        return cls(namespace=namespace, path=tuple(path))

    @classmethod
    def namespace_from_url(cls, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        return ".".join(reversed(parsed.netloc.split(".")))

    def get_sanitized_path(self) -> Path:
        namespace = (
            f"{sanitize_filename(self.namespace)}-{generate_md5_hash(self.namespace)}"
        )
        return Path(namespace, *self.path)

    def is_subpart_of(self, base: Identifier) -> bool:
        return (
            self.namespace == base.namespace
            and self.path[: len(base.path)] == base.path
        )

    def join(self, *path: str) -> Identifier:
        return Identifier(namespace=self.namespace, path=(*self.path, *path))

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

from __future__ import annotations

import abc
import typing

type Action = typing.LiteralString


class Permission(abc.ABC):
    @property
    @abc.abstractmethod
    def owner(self) -> str: ...

    @abc.abstractmethod
    def has(self, action: Action) -> bool: ...

    @abc.abstractmethod
    def add(self, action: Action) -> None: ...

    @abc.abstractmethod
    def remove(self, action: Action) -> None: ...

    @abc.abstractmethod
    def to_json(self) -> dict: ...

    @classmethod
    @abc.abstractmethod
    def from_json(cls, json: dict) -> Permission: ...


class Permissions(Permission):
    def __init__(self, owner: str, permissions: set[Action] | None = None) -> None:
        self._owner = owner
        self._permissions = permissions or set()

    @property
    def owner(self) -> str:
        return self._owner

    def has(self, action: Action) -> bool:
        return action in self._permissions

    def add(self, action: Action) -> None:
        self._permissions.add(action)

    def remove(self, action: Action) -> None:
        self._permissions.remove(action)

    def to_json(self) -> dict:
        return {"owner": self.owner, "permissions": list(self._permissions)}

    @classmethod
    def from_json(cls, json: dict) -> Permission:
        return cls(json["owner"], set(json["permissions"]))


class AdminPermissions(Permission):
    def __init__(self, owner: str) -> None:
        self._owner = owner

    @property
    def owner(self) -> str:
        return self._owner

    def has(self, action: Action) -> bool:
        return True

    def add(self, action: Action) -> None:
        pass

    def remove(self, action: Action) -> None:
        pass

    def to_json(self) -> dict:
        return {"owner": self.owner}

    @classmethod
    def from_json(cls, json: dict) -> Permission:
        return cls(json["owner"])

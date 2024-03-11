import json
from typing import Any

from omu import Identifier
from omu.extension.registry.registry_extension import (
    RegistryEventData,
    RegistryUpdateEvent,
)

from omuserver.server import Server
from omuserver.session import Session


class Registry:
    def __init__(self, server: Server, identifier: Identifier) -> None:
        self._key = identifier.key()
        self._registry = {}
        self._listeners: dict[str, Session] = {}
        self._path = server.directories.get(
            "registry"
        ) / identifier.to_path().with_suffix(".json")
        self._changed = False
        self.data = None

    async def load(self) -> Any:
        if self.data is None:
            if self._path.exists():
                self.data = json.loads(self._path.read_text())
            else:
                self.data = None
        return self.data

    async def store(self, value: Any) -> None:
        self.data = value
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(value))
        await self._notify()

    async def _notify(self) -> None:
        for listener in self._listeners.values():
            if listener.closed:
                raise Exception(f"Session {listener.app=} closed")
            await listener.send(
                RegistryUpdateEvent,
                RegistryEventData(key=self._key, value=self.data),
            )

    async def attach_session(self, session: Session) -> None:
        if session.app.key() in self._listeners:
            del self._listeners[session.app.key()]
        self._listeners[session.app.key()] = session
        session.listeners.disconnected += self.detach_session
        await session.send(
            RegistryUpdateEvent, RegistryEventData(key=self._key, value=self.data)
        )

    async def detach_session(self, session: Session) -> None:
        if session.app.key() not in self._listeners:
            raise Exception("Session not attached")
        del self._listeners[session.app.key()]
        session.listeners.disconnected -= self.detach_session

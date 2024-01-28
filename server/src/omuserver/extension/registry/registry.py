import json
from typing import Any

from omu.extension.registry.registry_extension import (
    RegistryEventData,
    RegistryUpdateEvent,
)

from omuserver.server import Server
from omuserver.session import Session
from omuserver.session.session import SessionListener


class Registry(SessionListener):
    def __init__(self, server: Server, app: str, name: str) -> None:
        self._key = f"{app}:{name}"
        self._registry = {}
        self._listeners: set[Session] = set()
        self._path = server.directories.get("registry") / app / f"{name}.json"
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
        for listener in self._listeners:
            await listener.send(
                RegistryUpdateEvent, RegistryEventData(key=self._key, value=self.data)
            )

    async def attach(self, session: Session) -> None:
        if session in self._listeners:
            raise Exception("Session already attached")
        self._listeners.add(session)
        session.add_listener(self)
        await session.send(
            RegistryUpdateEvent, RegistryEventData(key=self._key, value=self.data)
        )

    async def on_disconnected(self, session: Session) -> None:
        if session not in self._listeners:
            raise Exception("Session not attached")
        self._listeners.remove(session)
        session.remove_listener(self)

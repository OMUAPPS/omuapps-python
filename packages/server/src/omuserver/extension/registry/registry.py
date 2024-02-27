import json
from typing import Any

from omu.extension.registry.registry_extension import (
    RegistryEventData,
    RegistryUpdateEvent,
)
from omuserver.helper import generate_md5_hash, sanitize_filename

from omuserver.server import Server
from omuserver.session import Session
from omuserver.session.session import SessionListener


class Registry(SessionListener):
    def __init__(self, server: Server, namespace: str, name: str) -> None:
        self._key = f"{namespace}:{name}"
        self._registry = {}
        self._listeners: dict[str, Session] = {}
        namespace = f"{sanitize_filename(namespace)}-{generate_md5_hash(namespace)}"
        self._path = server.directories.get("registry") / namespace / f"{name}.json"
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
                RegistryUpdateEvent, RegistryEventData(key=self._key, value=self.data)
            )

    async def attach(self, session: Session) -> None:
        if session.app.key() in self._listeners:
            del self._listeners[session.app.key()]
        self._listeners[session.app.key()] = session
        session.add_listener(self)
        await session.send(
            RegistryUpdateEvent, RegistryEventData(key=self._key, value=self.data)
        )

    async def on_disconnected(self, session: Session) -> None:
        if session.app.key() not in self._listeners:
            raise Exception("Session not attached")
        del self._listeners[session.app.key()]
        session.remove_listener(self)

from omu import Identifier
from omu.extension.registry.packets import RegistryPermissions
from omu.extension.registry.registry_extension import (
    REGISTRY_UPDATE_PACKET,
    RegistryPacket,
)
from omu.serializer import Serializable

from omuserver.server import Server
from omuserver.session import Session


class ServerRegistry:
    def __init__(
        self,
        server: Server,
        id: Identifier,
        permissions: RegistryPermissions | None = None,
    ) -> None:
        self.id = id
        self.permissions = permissions or RegistryPermissions()
        self._listeners: dict[Identifier, Session] = {}
        self._path = server.directories.get(
            "registry"
        ) / id.get_sanitized_path().with_suffix(".json")
        self._changed = False
        self.data: bytes | None = None

    async def load(self):
        if self._path.exists():
            self.data = self._path.read_bytes()

    async def store(self, value: bytes | None) -> None:
        self.data = value
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if value is None:
            self._path.unlink(missing_ok=True)
        else:
            self._path.write_bytes(value)
        await self._notify()

    async def _notify(self) -> None:
        for listener in self._listeners.values():
            if listener.closed:
                raise Exception(f"Session {listener.app=} closed")
            await listener.send(
                REGISTRY_UPDATE_PACKET,
                RegistryPacket(id=self.id, value=self.data),
            )

    async def attach_session(self, session: Session) -> None:
        if session.app.id in self._listeners:
            raise Exception("Session already attached")
        self._listeners[session.app.id] = session
        session.listeners.disconnected += self.detach_session
        await session.send(
            REGISTRY_UPDATE_PACKET,
            RegistryPacket(id=self.id, value=self.data),
        )

    async def detach_session(self, session: Session) -> None:
        if session.app.id not in self._listeners:
            raise Exception("Session not attached")
        del self._listeners[session.app.id]
        session.listeners.disconnected -= self.detach_session


class Registry[T]:
    def __init__(
        self,
        registry: ServerRegistry,
        default_value: T,
        serializer: Serializable[T, bytes],
    ) -> None:
        self._registry = registry
        self._default_value = default_value
        self._serializer = serializer

    async def get(self) -> T:
        if self._registry.data is None:
            return self._default_value
        return self._serializer.deserialize(self._registry.data)

    async def set(self, value: T) -> None:
        await self._registry.store(self._serializer.serialize(value))

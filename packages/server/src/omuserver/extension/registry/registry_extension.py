from __future__ import annotations

from typing import TYPE_CHECKING, Dict

from omu.extension.registry.registry_extension import (
    REGISTRY_GET_ENDPOINT,
    REGISTRY_LISTEN_PACKET,
    REGISTRY_UPDATE_PACKET,
    RegistryData,
)
from omu.identifier import Identifier
from omu.serializer import Serializable

from omuserver.session import Session

from .registry import Registry, ServerRegistry

if TYPE_CHECKING:
    from omuserver.server import Server


class RegistryExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        server.packet_dispatcher.register(
            REGISTRY_LISTEN_PACKET, REGISTRY_UPDATE_PACKET
        )
        server.packet_dispatcher.add_packet_handler(
            REGISTRY_LISTEN_PACKET, self._on_listen
        )
        server.packet_dispatcher.add_packet_handler(
            REGISTRY_UPDATE_PACKET, self._on_update
        )
        server.endpoints.bind_endpoint(REGISTRY_GET_ENDPOINT, self._on_get)
        self.registries: Dict[Identifier, ServerRegistry] = {}

    async def _on_listen(self, session: Session, key: str) -> None:
        registry = await self.get(key)
        await registry.attach_session(session)

    async def _on_update(self, session: Session, event: RegistryData) -> None:
        registry = await self.get(event.key)
        await registry.store(event.value)

    async def _on_get(self, session: Session, key: str) -> RegistryData:
        registry = await self.get(key)
        return RegistryData(key, registry.existing, registry.data)

    async def get(self, key: str) -> ServerRegistry:
        identifier = Identifier.from_key(key)
        registry = self.registries.get(identifier)
        if registry is None:
            registry = ServerRegistry(self._server, identifier)
            self.registries[identifier] = registry
            await registry.load()
        return registry

    async def create[T](
        self, key: str, default_value: T, serializer: Serializable[T, bytes]
    ) -> Registry[T]:
        server_registry = await self.get(key)
        return Registry(server_registry, default_value, serializer)

    async def store(self, key: str, value: bytes) -> None:
        registry = await self.get(key)
        await registry.store(value)

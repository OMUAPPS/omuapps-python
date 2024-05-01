from __future__ import annotations

from typing import TYPE_CHECKING

from omu.extension.permission.permission import PermissionType
from omu.extension.registry.registry_extension import (
    REGISTRY_GET_ENDPOINT,
    REGISTRY_LISTEN_PACKET,
    REGISTRY_PERMISSION_ID,
    REGISTRY_UPDATE_PACKET,
    RegistryPacket,
)

from .registry import Registry, ServerRegistry

if TYPE_CHECKING:
    from omu.extension.registry import RegistryType
    from omu.identifier import Identifier

    from omuserver.server import Server
    from omuserver.session import Session

REGISTRY_PERMISSION = PermissionType(
    REGISTRY_PERMISSION_ID,
    {
        "level": "low",
        "name": {
            "en": "Registry Permission",
            "ja": "レジストリ権限",
        },
        "note": {
            "en": "Permission to read and write to a registry",
            "ja": "レジストリに読み書きする権限",
        },
    },
)


class RegistryExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        self.registries: dict[Identifier, ServerRegistry] = {}
        self._startup_registries: list[ServerRegistry] = []
        server.permissions.register(REGISTRY_PERMISSION)
        server.packet_dispatcher.register(
            REGISTRY_LISTEN_PACKET,
            REGISTRY_UPDATE_PACKET,
        )
        server.packet_dispatcher.add_packet_handler(
            REGISTRY_LISTEN_PACKET, self.handle_listen
        )
        server.packet_dispatcher.add_packet_handler(
            REGISTRY_UPDATE_PACKET, self.handle_update
        )
        server.endpoints.bind_endpoint(REGISTRY_GET_ENDPOINT, self.handle_get)
        server.listeners.start += self._on_start

    async def _on_start(self) -> None:
        for registry in self._startup_registries:
            await registry.load()
        self._startup_registries.clear()

    async def handle_listen(self, session: Session, identifier: Identifier) -> None:
        registry = await self.get(identifier)
        await registry.attach_session(session)

    async def handle_update(self, session: Session, event: RegistryPacket) -> None:
        registry = await self.get(event.identifier)
        await registry.store(event.value)

    async def handle_get(
        self, session: Session, identifier: Identifier
    ) -> RegistryPacket:
        registry = await self.get(identifier)
        return RegistryPacket(identifier, registry.data)

    async def get(self, identifier: Identifier) -> ServerRegistry:
        registry = self.registries.get(identifier)
        if registry is None:
            registry = ServerRegistry(self._server, identifier)
            self.registries[identifier] = registry
            await registry.load()
        return registry

    def create[T](
        self,
        registry_type: RegistryType[T],
    ) -> Registry[T]:
        registry = self.registries.get(registry_type.identifier)
        if registry is None:
            registry = ServerRegistry(self._server, registry_type.identifier)
            self.registries[registry_type.identifier] = registry
            self._startup_registries.append(registry)
        return Registry(
            registry,
            registry_type.default_value,
            registry_type.serializer,
        )

    async def store(self, identifier: Identifier, value: bytes) -> None:
        registry = await self.get(identifier)
        await registry.store(value)

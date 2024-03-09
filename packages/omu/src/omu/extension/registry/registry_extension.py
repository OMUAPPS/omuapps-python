from __future__ import annotations

from typing import Any, Awaitable, Callable, List, TypedDict

from omu.client import Client
from omu.event import JsonEventType
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import JsonEndpointType
from omu.identifier import Identifier

from .registry import Registry

RegistryExtensionType = ExtensionType(
    "registry",
    lambda client: RegistryExtension(client),
    lambda: [],
)


class RegistryEventData(TypedDict):
    key: str
    value: Any


RegistryUpdateEvent = JsonEventType[RegistryEventData].of_extension(
    RegistryExtensionType, "update"
)
RegistryListenEvent = JsonEventType[str].of_extension(RegistryExtensionType, "listen")
RegistryGetEndpoint = JsonEndpointType[str, Any].of_extension(
    RegistryExtensionType, "get"
)

type Coro[**P, R] = Callable[P, Awaitable[R]]


class RegistryExtension(Extension):
    def __init__(self, client: Client) -> None:
        self.client = client
        client.events.register(RegistryUpdateEvent)

    def get[T](self, identifier: Identifier, default_value: T) -> Registry[T]:
        return RegistryImpl(self.client, identifier, default_value)

    def create[T](self, name: str, default_value: T) -> Registry[T]:
        return self.get(self.client.app.identifier / name, default_value)


class RegistryImpl[T](Registry[T]):
    def __init__(
        self, client: Client, identifier: Identifier, default_value: T
    ) -> None:
        self.client = client
        self.identifier = identifier
        self.default_value = default_value
        self.key = identifier.key()
        self.listeners: List[Coro[[T], None]] = []
        self.listening = False
        client.events.add_listener(RegistryUpdateEvent, self._on_update)

    async def get(self) -> T:
        return (
            await self.client.endpoints.call(RegistryGetEndpoint, self.key)
        ) or self.default_value

    async def update(self, fn: Coro[[T], T]) -> None:
        value = await self.get()
        new_value = await fn(value)
        await self.client.send(
            RegistryUpdateEvent, RegistryEventData(key=self.key, value=new_value)
        )

    def listen(self, handler: Coro[[T], None]) -> Callable[[], None]:
        if not self.listening:
            self.client.connection.add_task(
                lambda: self.client.send(RegistryListenEvent, self.key)
            )
            self.listening = True

        self.listeners.append(handler)
        return lambda: self.listeners.remove(handler)

    async def _on_update(self, event: RegistryEventData) -> None:
        if event["key"] != self.key:
            return
        for listener in self.listeners:
            await listener(event["value"])

from typing import Any, Awaitable, Callable, TypedDict

from omu.client.client import Client
from omu.connection.connection import ConnectionListener
from omu.event.event import JsonEventType
from omu.extension.endpoint.endpoint import JsonEndpointType
from omu.extension.extension import Extension, define_extension_type

RegistryExtensionType = define_extension_type(
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


class RegistryExtension(Extension, ConnectionListener):
    def __init__(self, client: Client) -> None:
        self.client = client
        self._listen_keys: set[str] = set()
        client.events.register(RegistryUpdateEvent, RegistryListenEvent)
        client.connection.add_listener(self)

    async def get[T](self, name: str, app: str | None = None) -> T:
        data: T = await self.client.endpoints.call(
            RegistryGetEndpoint, f"{app or self.client.app.key()}:{name}"
        )
        return data

    async def set[T](self, name: str, value: T, app: str | None = None) -> None:
        await self.client.send(
            RegistryUpdateEvent,
            RegistryEventData(
                key=f"{app or self.client.app.key()}:{name}", value=value
            ),
        )

    def listen[T](
        self, name: str, app: str | None = None
    ) -> Callable[[Coro[[T], None]], None]:
        key = f"{app or self.client.app.key()}:{name}"

        def decorator(callback: Coro[[T], None]) -> None:
            self._listen_keys.add(key)

            async def wrapper(event: RegistryEventData) -> None:
                if event["key"] != key:
                    return
                await callback(event["value"])

            self.client.events.add_listener(RegistryUpdateEvent, wrapper)

        return decorator

    async def on_connected(self) -> None:
        for key in self._listen_keys:
            await self.client.send(RegistryListenEvent, key)

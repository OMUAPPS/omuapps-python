from typing import Any, Awaitable, Callable, TypedDict

from omu.client.client import Client
from omu.connection.connection import ConnectionListener
from omu.event.event import JsonEventType
from omu.extension.extension import Extension, define_extension_type

MessageExtensionType = define_extension_type(
    "message",
    lambda client: MessageExtension(client),
    lambda: [],
)


class MessageEventData(TypedDict):
    key: str
    body: Any


MessageRegisterEvent = JsonEventType[str].of_extension(MessageExtensionType, "register")
MessageListenEvent = JsonEventType[str].of_extension(MessageExtensionType, "listen")
MessageBroadcastEvent = JsonEventType[MessageEventData].of_extension(
    MessageExtensionType, "broadcast"
)

type Coro[**P, R] = Callable[P, Awaitable[R]]


class MessageKey[T]:
    def __init__(self, name: str, app: str, _t: type[T]):
        self.name = name
        self.app = app
        self.key = f"{self.app}:{self.name}"


class MessageExtension(Extension, ConnectionListener):
    def __init__(self, client: Client):
        self.client = client
        self._listen_keys: set[str] = set()
        self._keys: set[str] = set()
        client.events.register(
            MessageRegisterEvent, MessageListenEvent, MessageBroadcastEvent
        )
        client.connection.add_listener(self)

    def register[T](self, name: str, _t: type[T]) -> MessageKey[T]:
        key = f"{self.client.app.key()}:{name}"
        if key in self._keys:
            raise Exception(f"Key {key} is already registered")
        self._keys.add(key)
        return MessageKey(name, self.client.app.key(), _t)

    async def broadcast[T](self, key: MessageKey[T], body: T) -> None:
        await self.client.send(
            MessageBroadcastEvent,
            MessageEventData(key=key.key, body=body),
        )

    def listen[T](
        self, name: str, app: str | None = None
    ) -> Callable[[Coro[[T | None], None]], None]:
        key = f"{app or self.client.app.key()}:{name}"

        def decorator(callback: Coro[[T | None], None]) -> None:
            self._listen_keys.add(key)

            async def wrapper(event: MessageEventData) -> None:
                if event["key"] == key:
                    await callback(event["body"])

            self.client.events.add_listener(MessageBroadcastEvent, wrapper)

        return decorator

    async def on_connected(self) -> None:
        for key in self._keys:
            await self.client.send(MessageRegisterEvent, key)

from __future__ import annotations

from asyncio import Future
from typing import Any, Awaitable, Callable, Dict, Tuple, TypedDict

from omu.client import Client
from omu.connection import ConnectionListener
from omu.event.event import JsonEventType, SerializeEventType
from omu.extension.endpoint.endpoint import EndpointType, JsonEndpointType
from omu.extension.endpoint.model.endpoint_info import EndpointInfo
from omu.extension.extension import Extension, define_extension_type
from omu.extension.table.table import ModelTableType
from omu.interface import Serializer

EndpointExtensionType = define_extension_type(
    "endpoint",
    lambda client: EndpointExtension(client),
    lambda: [],
)

type Coro[**P, R] = Callable[P, Awaitable[R]]


class EndpointExtension(Extension, ConnectionListener):
    def __init__(self, client: Client) -> None:
        self.client = client
        self.promises: Dict[int, Future] = {}
        self.endpoints: Dict[str, Tuple[EndpointType, Coro[[Any], Any]]] = {}
        self.call_id = 0
        client.events.register(
            EndpointCallEvent, EndpointReceiveEvent, EndpointErrorEvent
        )
        client.events.add_listener(EndpointReceiveEvent, self._on_receive)
        client.events.add_listener(EndpointErrorEvent, self._on_error)
        client.events.add_listener(EndpointCallEvent, self._on_call)
        client.connection.add_listener(self)

    async def _on_receive(self, data: EndpointDataReq) -> None:
        if data["id"] not in self.promises:
            return
        future = self.promises[data["id"]]
        future.set_result(data["data"])
        self.promises.pop(data["id"])

    async def _on_error(self, data: EndpointError) -> None:
        if data["id"] not in self.promises:
            return
        future = self.promises[data["id"]]
        future.set_exception(Exception(data["error"]))

    async def _on_call(self, data: EndpointDataReq) -> None:
        if data["type"] not in self.endpoints:
            return
        endpoint, func = self.endpoints[data["type"]]
        try:
            req = endpoint.request_serializer.deserialize(data["data"])
            res = await func(req)
            json = endpoint.response_serializer.serialize(res)
            await self.client.send(
                EndpointReceiveEvent,
                EndpointDataReq(type=data["type"], id=data["id"], data=json),
            )
        except Exception as e:
            await self.client.send(
                EndpointErrorEvent,
                EndpointError(type=data["type"], id=data["id"], error=str(e)),
            )
            raise e

    async def on_connected(self) -> None:
        for endpoint, func in self.endpoints.values():
            await self.client.send(EndpointRegisterEvent, endpoint.info)

    def register[Req, Res](
        self, type: EndpointType[Req, Res, Any, Any], func: Coro[[Req], Res]
    ) -> None:
        if type.info.key() in self.endpoints:
            raise Exception(f"Endpoint for key {type.info.key()} already registered")
        self.endpoints[type.info.key()] = (type, func)

    def listen(
        self, func: Coro | None = None, name: str | None = None, app: str | None = None
    ) -> Callable[[Coro], Coro]:
        def decorator(func: Coro) -> Coro:
            info = EndpointInfo(
                owner=app or self.client.app.key(),
                name=name or func.__name__,
                description=getattr(func, "__doc__", ""),
            )
            type = JsonEndpointType(info)
            self.register(type, func)
            return func

        if func:
            decorator(func)
        return decorator

    async def call[Req, ResData, Res](
        self, endpoint: EndpointType[Req, Res, Any, ResData], data: Req
    ) -> Res:
        try:
            self.call_id += 1
            future = Future[ResData]()
            self.promises[self.call_id] = future
            json = endpoint.request_serializer.serialize(data)
            await self.client.send(
                EndpointCallEvent,
                EndpointDataReq(type=endpoint.info.key(), id=self.call_id, data=json),
            )
            res = await future
            return endpoint.response_serializer.deserialize(res)
        except Exception as e:
            raise Exception(f"Error calling endpoint {endpoint.info.key()}") from e


class EndpointReq(TypedDict):
    type: str
    id: int


class EndpointDataReq(TypedDict):
    type: str
    id: int
    data: Any


class EndpointError(TypedDict):
    type: str
    id: int
    error: str


EndpointRegisterEvent = SerializeEventType.of_extension(
    EndpointExtensionType, "register", Serializer.model(EndpointInfo)
)


EndpointCallEvent = JsonEventType[EndpointDataReq].of_extension(
    EndpointExtensionType,
    "call",
)
EndpointReceiveEvent = JsonEventType[EndpointDataReq].of_extension(
    EndpointExtensionType,
    "receive",
)
EndpointErrorEvent = JsonEventType[EndpointError].of_extension(
    EndpointExtensionType,
    "error",
)
EndpointsTableType = ModelTableType.of_extension(
    EndpointExtensionType,
    "endpoints",
    EndpointInfo,
)

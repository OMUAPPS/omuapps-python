from __future__ import annotations

from asyncio import Future
from typing import Any, Awaitable, Callable, Dict, Tuple, TypedDict

from omu.client import Client
from omu.event import JsonEventType, SerializeEventType
from omu.extension.endpoint import EndpointInfo, EndpointType, JsonEndpointType
from omu.extension.extension import Extension, ExtensionType
from omu.extension.table import TableType
from omu.identifier import Identifier
from omu.network import ConnectionListener
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.serializer import Serializable, Serializer

EndpointExtensionType = ExtensionType(
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
            res_data = endpoint.response_serializer.serialize(res)
            await self.client.send(
                EndpointReceiveEvent,
                EndpointDataReq(type=data["type"], id=data["id"], data=res_data),
            )
        except Exception as e:
            await self.client.send(
                EndpointErrorEvent,
                EndpointError(type=data["type"], id=data["id"], error=str(e)),
            )
            raise e

    async def on_connected(self) -> None:
        for endpoint, _ in self.endpoints.values():
            await self.client.send(EndpointRegisterEvent, endpoint.info)

    def register[Req, Res](
        self, type: EndpointType[Req, Res], func: Coro[[Req], Res]
    ) -> None:
        if type.info.key() in self.endpoints:
            raise Exception(f"Endpoint for key {type.info.key()} already registered")
        self.endpoints[type.info.key()] = (type, func)

    def listen(
        self, func: Coro | None = None, name: str | None = None, app: str | None = None
    ) -> Callable[[Coro], Coro]:
        def decorator(func: Coro) -> Coro:
            info = EndpointInfo(
                identifier=Identifier.create(
                    app or self.client.app.key(), name or func.__name__
                ),
                description=getattr(func, "__doc__", ""),
            )
            type = JsonEndpointType(info)
            self.register(type, func)
            return func

        if func:
            decorator(func)
        return decorator

    async def call[Req, Res](self, endpoint: EndpointType[Req, Res], data: Req) -> Res:
        try:
            self.call_id += 1
            future = Future[bytes]()
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


class EndpointDataReq(EndpointReq):
    type: str
    id: int
    data: bytes


class EndpointError(EndpointReq):
    type: str
    id: int
    error: str


EndpointRegisterEvent = JsonEventType.of_extension(
    EndpointExtensionType,
    "register",
    Serializer.model(EndpointInfo),
)


class CallSerializer(Serializable[EndpointDataReq, bytes]):
    def serialize(self, item: EndpointDataReq) -> bytes:
        writer = ByteWriter()
        writer.write_string(item["type"])
        writer.write_int(item["id"])
        writer.write_byte_array(item["data"])
        return writer.finish()

    def deserialize(self, item: bytes) -> EndpointDataReq:
        with ByteReader(item) as reader:
            type = reader.read_string()
            id = reader.read_int()
            data = reader.read_byte_array()
        return EndpointDataReq(type=type, id=id, data=data)


CALL_SERIALIZER = CallSerializer()

EndpointCallEvent = SerializeEventType[EndpointDataReq].of_extension(
    EndpointExtensionType,
    "call",
    CALL_SERIALIZER,
)
EndpointReceiveEvent = SerializeEventType[EndpointDataReq].of_extension(
    EndpointExtensionType,
    "receive",
    CALL_SERIALIZER,
)
EndpointErrorEvent = JsonEventType[EndpointError].of_extension(
    EndpointExtensionType,
    "error",
)
EndpointsTableType = TableType.model(
    EndpointExtensionType,
    "endpoints",
    EndpointInfo,
)

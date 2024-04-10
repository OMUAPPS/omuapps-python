from __future__ import annotations

from asyncio import Future
from typing import Any, Callable, Dict, List, Tuple, TypedDict

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.helper import Coro
from omu.identifier import Identifier
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.network.packet import PacketType
from omu.serializer import Serializer

from .endpoint import EndpointType

ENDPOINT_EXTENSION_TYPE = ExtensionType(
    "endpoint",
    lambda client: EndpointExtension(client),
    lambda: [],
)


class EndpointExtension(Extension):
    def __init__(self, client: Client) -> None:
        self.client = client
        self.response_promises: Dict[int, Future] = {}
        self.endpoints: Dict[Identifier, Tuple[EndpointType, Coro[[Any], Any]]] = {}
        self.call_id = 0
        client.network.register_packet(
            ENDPOINT_REGISTER_PACKET,
            ENDPOINT_CALL_PACKET,
            ENDPOINT_RECEIVE_PACKET,
            ENDPOINT_ERROR_PACKET,
        )
        client.network.add_packet_handler(ENDPOINT_RECEIVE_PACKET, self._on_receive)
        client.network.add_packet_handler(ENDPOINT_ERROR_PACKET, self._on_error)
        client.network.add_packet_handler(ENDPOINT_CALL_PACKET, self._on_call)
        client.network.listeners.connected += self.on_connected

    async def _on_receive(self, data: EndpointDataPacket) -> None:
        if data["id"] not in self.response_promises:
            raise Exception(f"Received response for unknown call id {data['id']}")
        future = self.response_promises.pop(data["id"])
        future.set_result(data["data"])

    async def _on_error(self, data: EndpointErrorPacket) -> None:
        if data["id"] not in self.response_promises:
            raise Exception(f"Received error for unknown call id {data['id']}")
        future = self.response_promises.pop(data["id"])
        future.set_exception(Exception(data["error"]))

    async def _on_call(self, data: EndpointDataPacket) -> None:
        endpoint_id = Identifier.from_key(data["type"])
        if endpoint_id not in self.endpoints:
            raise Exception(f"Received call for unknown endpoint {endpoint_id}")
        endpoint, func = self.endpoints[endpoint_id]
        try:
            req = endpoint.request_serializer.deserialize(data["data"])
            res = await func(req)
            res_data = endpoint.response_serializer.serialize(res)
            await self.client.send(
                ENDPOINT_RECEIVE_PACKET,
                EndpointDataPacket(type=data["type"], id=data["id"], data=res_data),
            )
        except Exception as e:
            await self.client.send(
                ENDPOINT_ERROR_PACKET,
                EndpointErrorPacket(type=data["type"], id=data["id"], error=str(e)),
            )
            raise e

    async def on_connected(self) -> None:
        await self.client.send(ENDPOINT_REGISTER_PACKET, [*self.endpoints.keys()])

    def register[Req, Res](
        self, type: EndpointType[Req, Res], func: Coro[[Req], Res]
    ) -> None:
        if type.identifier in self.endpoints:
            raise Exception(f"Endpoint for key {type.identifier} already registered")
        self.endpoints[type.identifier] = (type, func)

    def bind[T, R](
        self,
        handler: Coro[[T], R] | None = None,
        endpoint_type: EndpointType[T, R] | None = None,
    ):
        if endpoint_type is None:
            raise Exception("Endpoint type must be provided")

        def decorator(func: Coro[[T], R]) -> Coro[[T], R]:
            self.register(endpoint_type, func)
            return func

        if handler:
            decorator(handler)
        return decorator

    def listen(
        self, handler: Coro | None = None, name: str | None = None
    ) -> Callable[[Coro], Coro]:
        def decorator(func: Coro) -> Coro:
            type = EndpointType.create_json(
                self.client.app.identifier,
                name or func.__name__,
            )
            self.register(type, func)
            return func

        if handler:
            decorator(handler)
        return decorator

    async def call[Req, Res](self, endpoint: EndpointType[Req, Res], data: Req) -> Res:
        try:
            self.call_id += 1
            future = Future[bytes]()
            self.response_promises[self.call_id] = future
            json = endpoint.request_serializer.serialize(data)
            await self.client.send(
                ENDPOINT_CALL_PACKET,
                EndpointDataPacket(
                    type=endpoint.identifier.key(), id=self.call_id, data=json
                ),
            )
            res = await future
            return endpoint.response_serializer.deserialize(res)
        except Exception as e:
            raise Exception(
                f"Error calling endpoint {endpoint.identifier.key()}"
            ) from e


class EndpointPacket(TypedDict):
    type: str
    id: int


class EndpointDataPacket(EndpointPacket):
    data: bytes


class EndpointErrorPacket(EndpointPacket):
    error: str


class ENDPOINT_DATA_SERIALIZER:
    @classmethod
    def serialize(cls, item: EndpointDataPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item["type"])
        writer.write_int(item["id"])
        writer.write_byte_array(item["data"])
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> EndpointDataPacket:
        with ByteReader(item) as reader:
            type = reader.read_string()
            id = reader.read_int()
            data = reader.read_byte_array()
        return EndpointDataPacket(type=type, id=id, data=data)


ENDPOINT_REGISTER_PACKET = PacketType[List[Identifier]].create_json(
    ENDPOINT_EXTENSION_TYPE,
    "register",
    Serializer.model(Identifier).to_array(),
)
ENDPOINT_CALL_PACKET = PacketType[EndpointDataPacket].create_serialized(
    ENDPOINT_EXTENSION_TYPE,
    "call",
    ENDPOINT_DATA_SERIALIZER,
)
ENDPOINT_RECEIVE_PACKET = PacketType[EndpointDataPacket].create_serialized(
    ENDPOINT_EXTENSION_TYPE,
    "receive",
    ENDPOINT_DATA_SERIALIZER,
)
ENDPOINT_ERROR_PACKET = PacketType[EndpointErrorPacket].create_json(
    ENDPOINT_EXTENSION_TYPE,
    "error",
)

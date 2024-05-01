from __future__ import annotations

import abc
from typing import Dict, Tuple

from loguru import logger
from omu.extension.endpoint.endpoint_extension import (
    ENDPOINT_CALL_PACKET,
    ENDPOINT_ERROR_PACKET,
    ENDPOINT_RECEIVE_PACKET,
    ENDPOINT_REGISTER_PACKET,
    EndpointDataPacket,
    EndpointErrorPacket,
    EndpointType,
)
from omu.extension.endpoint.packets import EndpointRegisterPacket
from omu.helper import Coro
from omu.identifier import Identifier

from omuserver.server import Server
from omuserver.session import Session


class Endpoint(abc.ABC):
    @property
    @abc.abstractmethod
    def id(self) -> Identifier: ...

    @property
    @abc.abstractmethod
    def permission(self) -> Identifier | None: ...

    @abc.abstractmethod
    async def call(self, data: EndpointDataPacket, session: Session) -> None: ...


class SessionEndpoint(Endpoint):
    def __init__(
        self,
        session: Session,
        id: Identifier,
        permission: Identifier | None,
    ) -> None:
        self._session = session
        self._id = id
        self._permission = permission

    @property
    def id(self) -> Identifier:
        return self._id

    @property
    def permission(self) -> Identifier | None:
        return self._permission

    async def call(self, data: EndpointDataPacket, session: Session) -> None:
        if self._session.closed:
            raise RuntimeError(f"Session {self._session.app.key()} already closed")
        await self._session.send(ENDPOINT_CALL_PACKET, data)


class ServerEndpoint[Req, Res](Endpoint):
    def __init__(
        self,
        server: Server,
        endpoint: EndpointType[Req, Res],
        callback: Coro[[Session, Req], Res],
        permission: Identifier | None = None,
    ) -> None:
        self._server = server
        self._endpoint = endpoint
        self._callback = callback
        self._permission = permission

    @property
    def id(self) -> Identifier:
        return self._endpoint.id

    @property
    def permission(self) -> Identifier | None:
        return self._permission

    async def call(self, data: EndpointDataPacket, session: Session) -> None:
        if session.closed:
            raise RuntimeError("Session already closed")
        try:
            req = self._endpoint.request_serializer.deserialize(data.data)
            res = await self._callback(session, req)
            json = self._endpoint.response_serializer.serialize(res)
            await session.send(
                ENDPOINT_RECEIVE_PACKET,
                EndpointDataPacket(id=data.id, key=data.key, data=json),
            )
        except Exception as e:
            await session.send(
                ENDPOINT_ERROR_PACKET,
                EndpointErrorPacket(id=data.id, key=data.key, error=str(e)),
            )
            raise e


class EndpointCall:
    def __init__(self, session: Session, data: EndpointDataPacket) -> None:
        self._session = session
        self._data = data

    async def receive(self, data: EndpointDataPacket) -> None:
        await self._session.send(ENDPOINT_RECEIVE_PACKET, data)

    async def error(self, error: str) -> None:
        await self._session.send(
            ENDPOINT_ERROR_PACKET,
            EndpointErrorPacket(id=self._data.id, key=self._data.key, error=error),
        )


class EndpointExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        self._endpoints: Dict[Identifier, Endpoint] = {}
        self._calls: Dict[Tuple[Identifier, int], EndpointCall] = {}
        server.packet_dispatcher.register(
            ENDPOINT_REGISTER_PACKET,
            ENDPOINT_CALL_PACKET,
            ENDPOINT_RECEIVE_PACKET,
            ENDPOINT_ERROR_PACKET,
        )
        server.packet_dispatcher.add_packet_handler(
            ENDPOINT_REGISTER_PACKET, self._on_endpoint_register
        )
        server.packet_dispatcher.add_packet_handler(
            ENDPOINT_CALL_PACKET, self._on_endpoint_call
        )
        server.packet_dispatcher.add_packet_handler(
            ENDPOINT_RECEIVE_PACKET, self._on_endpoint_receive
        )
        server.packet_dispatcher.add_packet_handler(
            ENDPOINT_ERROR_PACKET, self._on_endpoint_error
        )

    async def _on_endpoint_register(
        self, session: Session, packet: EndpointRegisterPacket
    ) -> None:
        for endpoint, permission in packet.endpoints.items():
            self._endpoints[endpoint] = SessionEndpoint(
                session=session,
                id=endpoint,
                permission=permission,
            )

    def bind_endpoint[Req, Res](
        self,
        type: EndpointType[Req, Res],
        callback: Coro[[Session, Req], Res],
    ) -> None:
        if type.id in self._endpoints:
            raise ValueError(f"Endpoint {type.id.key()} already bound")
        endpoint = ServerEndpoint(
            self._server,
            type,
            callback,
        )
        self._endpoints[type.id] = endpoint

    async def _on_endpoint_call(
        self, session: Session, req: EndpointDataPacket
    ) -> None:
        endpoint = await self._get_endpoint(req, session)
        if endpoint is None:
            logger.warning(
                f"{session.app.key()} tried to call unknown endpoint {req.id}"
            )
            await session.send(
                ENDPOINT_ERROR_PACKET,
                EndpointErrorPacket(
                    id=req.id,
                    key=req.key,
                    error=f"Endpoint {req.id} not found",
                ),
            )
            return
        if endpoint.permission is not None:
            if endpoint.id.is_subpart_of(session.app.identifier):
                has_permission = True
            else:
                has_permission = self._server.permissions.has_permission(
                    session, endpoint.permission
                )
            if not has_permission:
                logger.warning(
                    f"{session.app.key()} tried to call "
                    "endpoint {req.id} without permission"
                )
                await session.send(
                    ENDPOINT_ERROR_PACKET,
                    EndpointErrorPacket(
                        id=req.id,
                        key=req.key,
                        error=f"Permission denied for endpoint {req.id}",
                    ),
                )
                return
        await endpoint.call(req, session)
        key = (req.id, req.key)
        self._calls[key] = EndpointCall(session, req)

    async def _on_endpoint_receive(
        self, session: Session, req: EndpointDataPacket
    ) -> None:
        key = (req.id, req.key)
        call = self._calls.get(key)
        if call is None:
            await session.send(
                ENDPOINT_ERROR_PACKET,
                EndpointErrorPacket(
                    id=req.id,
                    key=req.key,
                    error=f"Endpoint not found {req.id}",
                ),
            )
            return
        await call.receive(req)

    async def _on_endpoint_error(
        self, session: Session, packet: EndpointErrorPacket
    ) -> None:
        key = (packet.id, packet.key)
        call = self._calls.get(key)
        if call is None:
            await session.send(
                ENDPOINT_ERROR_PACKET,
                EndpointErrorPacket(
                    id=packet.id,
                    key=packet.key,
                    error=f"Endpoint {packet.id} not found",
                ),
            )
        else:
            await call.error(packet.error)

    async def _get_endpoint(
        self, packet: EndpointDataPacket, session: Session
    ) -> Endpoint | None:
        endpoint = self._endpoints.get(packet.id)
        if endpoint is None:
            await session.send(
                ENDPOINT_ERROR_PACKET,
                EndpointErrorPacket(
                    id=packet.id,
                    key=packet.key,
                    error=f"Endpoint {packet.id} not found",
                ),
            )
            logger.warning(
                f"{session.app.key()} tried to call unconnected endpoint {packet.id}"
            )
            return
        return endpoint

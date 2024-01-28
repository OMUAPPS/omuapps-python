from __future__ import annotations

import abc
from typing import Any

from omu.connection.address import Address
from omu.extension.endpoint.model.endpoint_info import EndpointInfo
from omu.extension.extension import ExtensionType
from omu.extension.server.model.app import App
from omu.interface import Serializable, Serializer


class EndpointType[Req, Res, ReqData, ResData](abc.ABC):
    @property
    @abc.abstractmethod
    def info(self) -> EndpointInfo:
        ...

    @property
    @abc.abstractmethod
    def request_serializer(self) -> Serializable[Req, ReqData]:
        ...

    @property
    @abc.abstractmethod
    def response_serializer(self) -> Serializable[Res, ResData]:
        ...


class SerializeEndpointType[Req, Res](EndpointType[Req, Res, Any, Any]):
    def __init__(
        self,
        info: EndpointInfo,
        request_serializer: Serializable[Req, Any] | None = None,
        response_serializer: Serializable[Res, Any] | None = None,
    ):
        self._info = info
        self._request_serializer = request_serializer or Serializer.noop()
        self._response_serializer = response_serializer or Serializer.noop()

    @classmethod
    def of(
        cls,
        app: App,
        name: str,
        request_serializer: Serializable[Req, Any] | None = None,
        response_serializer: Serializable[Res, Any] | None = None,
    ):
        return cls(
            info=EndpointInfo(app.key(), name),
            request_serializer=request_serializer,
            response_serializer=response_serializer,
        )

    @classmethod
    def of_extension(
        cls,
        extension: ExtensionType,
        name: str,
        request_serializer: Serializable[Req, Any] | None = None,
        response_serializer: Serializable[Res, Any] | None = None,
    ):
        return cls(
            info=EndpointInfo(extension.key, name),
            request_serializer=request_serializer,
            response_serializer=response_serializer,
        )

    @property
    def info(self) -> EndpointInfo:
        return self._info

    @property
    def request_serializer(self) -> Serializable[Req, Any]:
        return self._request_serializer

    @property
    def response_serializer(self) -> Serializable[Res, Any]:
        return self._response_serializer


class JsonEndpointType[Req, Res](SerializeEndpointType[Req, Res]):
    def __init__(
        self,
        info: EndpointInfo,
    ):
        super().__init__(
            info,
            request_serializer=Serializer.noop(),
            response_serializer=Serializer.noop(),
        )

    @classmethod
    def of(
        cls,
        app: App,
        name: str,
    ):
        return cls(
            info=EndpointInfo(app.key(), name),
        )

    @classmethod
    def of_extension(
        cls,
        extension: ExtensionType,
        name: str,
    ):
        return cls(
            info=EndpointInfo(extension.key, name),
        )


class Endpoint(abc.ABC):
    @property
    @abc.abstractmethod
    def address(self) -> Address:
        ...

    @abc.abstractmethod
    async def execute[Req, Res](
        self, type: EndpointType[Req, Res, Any, Any], data: Req
    ) -> Res:
        ...

from __future__ import annotations

import abc
from typing import TYPE_CHECKING

from omu.identifier import Identifier
from omu.serializer import Serializable, Serializer

from .endpoint_info import EndpointInfo

if TYPE_CHECKING:
    from omu.extension import ExtensionType
    from omu.extension.server import App


class EndpointType[Req, Res](abc.ABC):
    @property
    @abc.abstractmethod
    def info(self) -> EndpointInfo:
        ...

    @property
    @abc.abstractmethod
    def request_serializer(self) -> Serializable[Req, bytes]:
        ...

    @property
    @abc.abstractmethod
    def response_serializer(self) -> Serializable[Res, bytes]:
        ...


class SerializeEndpointType[Req, Res](EndpointType[Req, Res]):
    def __init__(
        self,
        info: EndpointInfo,
        request_serializer: Serializable[Req, bytes],
        response_serializer: Serializable[Res, bytes],
    ):
        self._info = info
        self._request_serializer = request_serializer
        self._response_serializer = response_serializer

    @classmethod
    def of(
        cls,
        identifier: Identifier | App,
        name: str,
        request_serializer: Serializable[Req, bytes],
        response_serializer: Serializable[Res, bytes],
    ):
        return cls(
            info=EndpointInfo(identifier=Identifier.create(identifier.key(), name)),
            request_serializer=request_serializer,
            response_serializer=response_serializer,
        )

    @classmethod
    def of_extension(
        cls,
        extension: ExtensionType,
        name: str,
        request_serializer: Serializable[Req, bytes],
        response_serializer: Serializable[Res, bytes],
    ):
        return cls(
            info=EndpointInfo(identifier=Identifier.create(extension.name, name)),
            request_serializer=request_serializer,
            response_serializer=response_serializer,
        )

    @property
    def info(self) -> EndpointInfo:
        return self._info

    @property
    def request_serializer(self) -> Serializable[Req, bytes]:
        return self._request_serializer

    @property
    def response_serializer(self) -> Serializable[Res, bytes]:
        return self._response_serializer


class JsonEndpointType[Req, Res](SerializeEndpointType[Req, Res]):
    def __init__(
        self,
        info: EndpointInfo,
    ):
        super().__init__(
            info,
            request_serializer=Serializer.json(),
            response_serializer=Serializer.json(),
        )

    @classmethod
    def of(
        cls,
        identifier: Identifier | App,
        name: str,
    ):
        return cls(
            info=EndpointInfo(identifier=Identifier.create(identifier.key(), name)),
        )

    @classmethod
    def of_extension(
        cls,
        extension: ExtensionType,
        name: str,
    ):
        return cls(
            info=EndpointInfo(identifier=Identifier.create(extension.name, name)),
        )

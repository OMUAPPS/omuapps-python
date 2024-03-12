from __future__ import annotations

import abc
from typing import TYPE_CHECKING

from omu.identifier import Identifier
from omu.serializer import Serializable, Serializer

if TYPE_CHECKING:
    from omu.extension import ExtensionType


class EndpointType[Req, Res](abc.ABC):
    @property
    @abc.abstractmethod
    def identifier(self) -> Identifier: ...

    @property
    @abc.abstractmethod
    def request_serializer(self) -> Serializable[Req, bytes]: ...

    @property
    @abc.abstractmethod
    def response_serializer(self) -> Serializable[Res, bytes]: ...


class SerializeEndpointType[Req, Res](EndpointType[Req, Res]):
    def __init__(
        self,
        identifier: Identifier,
        request_serializer: Serializable[Req, bytes],
        response_serializer: Serializable[Res, bytes],
    ):
        self._identifier = identifier
        self._request_serializer = request_serializer
        self._response_serializer = response_serializer

    @classmethod
    def of(
        cls,
        identifier: Identifier,
        name: str,
        request_serializer: Serializable[Req, bytes],
        response_serializer: Serializable[Res, bytes],
    ):
        return cls(
            identifier=identifier / name,
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
            identifier=extension / name,
            request_serializer=request_serializer,
            response_serializer=response_serializer,
        )

    @property
    def identifier(self) -> Identifier:
        return self._identifier

    @property
    def request_serializer(self) -> Serializable[Req, bytes]:
        return self._request_serializer

    @property
    def response_serializer(self) -> Serializable[Res, bytes]:
        return self._response_serializer


class JsonEndpointType[Req, Res](SerializeEndpointType[Req, Res]):
    def __init__(
        self,
        identifier: Identifier,
    ):
        super().__init__(
            identifier=identifier,
            request_serializer=Serializer.json(),
            response_serializer=Serializer.json(),
        )

    @classmethod
    def of(
        cls,
        identifier: Identifier,
        name: str,
    ):
        return cls(
            identifier=identifier / name,
        )

    @classmethod
    def of_extension(
        cls,
        extension: ExtensionType,
        name: str,
    ):
        return cls(
            identifier=extension / name,
        )

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from omu.identifier import Identifier
from omu.serializer import Serializable, Serializer


@dataclass(frozen=True)
class EndpointType[Req, Res]:
    identifier: Identifier
    request_serializer: Serializable[Req, bytes]
    response_serializer: Serializable[Res, bytes]

    @classmethod
    def create_json(
        cls,
        identifier: Identifier,
        name: str,
        request_serializer: Serializable[Req, Any] | None = None,
        response_serializer: Serializable[Res, Any] | None = None,
    ):
        return cls(
            identifier=identifier / name,
            request_serializer=Serializer.of(
                request_serializer or Serializer.noop()
            ).pipe(Serializer.json()),
            response_serializer=Serializer.of(
                response_serializer or Serializer.noop()
            ).pipe(Serializer.json()),
        )

    @classmethod
    def create_serialized(
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

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from omu.identifier import Identifier
from omu.serializer import Serializable, Serializer


@dataclass
class EndpointType[Req, Res]:
    identifier: Final[Identifier]
    request_serializer: Final[Serializable[Req, bytes]]
    response_serializer: Final[Serializable[Res, bytes]]

    @classmethod
    def create_json(
        cls,
        identifier: Identifier,
        name: str,
    ):
        return cls(
            identifier=identifier / name,
            request_serializer=Serializer.json(),
            response_serializer=Serializer.json(),
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

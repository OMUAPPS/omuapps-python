import abc
from dataclasses import dataclass
from typing import Callable

from omu.helper import Coro
from omu.identifier import Identifier
from omu.serializer import Serializable, Serializer


@dataclass(frozen=True)
class MessageType[T]:
    identifier: Identifier
    serializer: Serializable[T, bytes]

    @classmethod
    def create_json(
        cls,
        identifier: Identifier,
        name: str,
    ):
        return cls(
            identifier=identifier / name,
            serializer=Serializer.json(),
        )

    @classmethod
    def create_serialized(
        cls,
        identifier: Identifier,
        name: str,
        serializer: Serializable[T, bytes],
    ):
        return cls(
            identifier=identifier / name,
            serializer=serializer,
        )


class Message[T](abc.ABC):
    @abc.abstractmethod
    def listen(self, listener: Coro[[T], None]) -> Callable[[], None]: ...

    @abc.abstractmethod
    async def broadcast(self, body: T) -> None: ...

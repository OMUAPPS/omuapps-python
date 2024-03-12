import abc
from typing import Callable

from omu.helper import Coro


class Message[T](abc.ABC):
    @abc.abstractmethod
    async def broadcast(self, body: T) -> None: ...

    @abc.abstractmethod
    def listen(self, fn: Coro[[T], None]) -> Callable[[], None]: ...

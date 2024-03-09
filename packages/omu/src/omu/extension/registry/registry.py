import abc
from typing import Callable

from omu.helper import Coro


class Registry[T](abc.ABC):
    @abc.abstractmethod
    async def get(self) -> T: ...

    @abc.abstractmethod
    async def update(self, fn: Callable[[T], T]) -> None: ...

    @abc.abstractmethod
    def listen(self, fn: Coro[[T], None]) -> Callable[[], None]: ...

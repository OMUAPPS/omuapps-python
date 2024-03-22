from __future__ import annotations

import hashlib
import re
import typing

type AsyncCallback[**P] = typing.Callable[P, typing.Coroutine[None, None, None]]
type Coro[**P, T] = typing.Callable[P, typing.Coroutine[None, None, T]]


def instance[T](cls: typing.Type[T]) -> T:
    return cls()


def map_optional[V, T](
    data: V | None, func: typing.Callable[[V], T], default: T | None = None
) -> T | None:
    if data is None:
        return default
    return func(data)


sanitize_re = re.compile(r"[^\w]")


def sanitize_filename(name: str) -> str:
    return sanitize_re.sub("_", name)


def generate_md5_hash(id: str) -> str:
    return hashlib.md5(id.encode()).hexdigest()

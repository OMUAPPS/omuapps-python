from __future__ import annotations

import io
import typing

type AsyncCallback[**P] = typing.Callable[P, typing.Awaitable]
type Coro[**P, T] = typing.Callable[P, typing.Awaitable[T]]


def instance[T](cls: typing.Type[T]) -> T:
    return cls()


def map_optional[V, T](
    data: V | None, func: typing.Callable[[V], T], default: T | None = None
) -> T | None:
    if data is None:
        return default
    return func(data)


class ByteWriter:
    def __init__(self, init: bytes | None = None) -> None:
        self.stream = io.BytesIO(init or b"")
        self.finished = False

    def write(self, data: bytes) -> ByteWriter:
        if self.finished:
            raise ValueError("Writer already finished")
        self.stream.write(data)
        return self

    def write_int(self, value: int) -> ByteWriter:
        self.write(value.to_bytes(4, "big"))
        return self

    def write_short(self, value: int) -> ByteWriter:
        self.write(value.to_bytes(2, "big"))
        return self

    def write_byte(self, value: int) -> ByteWriter:
        self.write(value.to_bytes(1, "big"))
        return self

    def write_byte_array(self, value: bytes) -> ByteWriter:
        if len(value) > 0xFFFFFFFF:
            raise ValueError("Byte array too large")
        self.write_int(len(value))
        self.write(value)
        return self

    def write_string(self, value: str) -> ByteWriter:
        self.write_byte_array(value.encode("utf-8"))
        return self

    def finish(self) -> bytes:
        if self.finished:
            raise ValueError("Writer already finished")
        self.finished = True
        return self.stream.getvalue()


class ByteReader:
    def __init__(self, buffer: bytes) -> None:
        self.stream = io.BytesIO(buffer)
        self.finished = False

    def read(self, size: int | None = None) -> bytes:
        if self.finished:
            raise ValueError("Reader already finished")
        return self.stream.read(size)

    def read_int(self) -> int:
        return int.from_bytes(self.read(4), "big")

    def read_short(self) -> int:
        return int.from_bytes(self.read(2), "big")

    def read_byte(self) -> int:
        return int.from_bytes(self.read(1), "big")

    def read_byte_array(self) -> bytes:
        length = self.read_int()
        return self.read(length)

    def read_string(self) -> str:
        return self.read_byte_array().decode("utf-8")

    def finish(self) -> None:
        if self.finished:
            raise ValueError("Reader already finished")
        self.finished = True
        if self.stream.read(1):
            raise ValueError("Reader not fully consumed")

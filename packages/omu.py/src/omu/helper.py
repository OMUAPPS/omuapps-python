import typing


def instance[T](cls: typing.Type[T]) -> T:
    return cls()


def map_optional[V, T](
    data: V | None, func: typing.Callable[[V], T], default: T | None = None
) -> T | None:
    if data is None:
        return default
    return func(data)

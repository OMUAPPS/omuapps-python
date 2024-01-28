import typing


def instance[T](cls: typing.Type[T]) -> T:
    return cls()

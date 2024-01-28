import abc


class Keyable(abc.ABC):
    @abc.abstractmethod
    def key(self) -> str:
        ...

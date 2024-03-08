from typing import AsyncGenerator, Callable, Dict, List, Mapping

from omu.extension.table import Table, TableListener, TableType, TableConfig
from omu.interface import Keyable
from omu.helper import AsyncCallback
from omu.serializer import Serializable

from .server_table import ServerTable, ServerTableListener

type Coro[**P, T] = Callable[P, T]


class SerializeAdapter[T: Keyable](Mapping[str, T]):
    def __init__(self, cache: Mapping[str, bytes], serializer: Serializable[T, bytes]):
        self._cache = cache
        self._serializer = serializer

    def __getitem__(self, key: str) -> T:
        return self._serializer.deserialize(self._cache[key])


class SerializedTable[T: Keyable](Table[T], ServerTableListener):
    def __init__(self, table: ServerTable, type: TableType[T]):
        self._table = table
        self._type = type
        self._listeners: List[TableListener[T]] = []
        self._proxies: List[Coro[[T], T | None]] = []
        self._chunk_size = 100
        self.key = type.identifier.key()
        table.add_listener(self)

    @property
    def cache(self) -> Mapping[str, T]:
        return SerializeAdapter(self._table.cache, self._type.serializer)

    def set_config(self, config: TableConfig) -> None:
        self._table.set_config(config)

    def set_cache_size(self, size: int) -> None:
        self._table.set_cache_size(size)

    async def get(self, key: str) -> T | None:
        if key in self._table.cache:
            return self._type.serializer.deserialize(self._table.cache[key])
        item = await self._table.get(key)
        if item is None:
            return None
        return self._type.serializer.deserialize(item)

    async def add(self, *items: T) -> None:
        data = {item.key(): self._type.serializer.serialize(item) for item in items}
        await self._table.add(data)

    async def update(self, *items: T) -> None:
        data = {item.key(): self._type.serializer.serialize(item) for item in items}
        await self._table.update(data)

    async def remove(self, *items: T) -> None:
        await self._table.remove([item.key() for item in items])

    async def clear(self) -> None:
        await self._table.clear()

    async def fetch_items(
        self,
        before: int | None = None,
        after: int | None = None,
        cursor: str | None = None,
    ) -> Dict[str, T]:
        items = await self._table.fetch_items(before, after, cursor)
        return self._parse_items(items)

    async def iterate(
        self,
        backward: bool = False,
        cursor: str | None = None,
    ) -> AsyncGenerator[T, None]:
        items = await self.fetch_items(
            before=self._chunk_size if backward else None,
            after=self._chunk_size if not backward else None,
            cursor=cursor,
        )
        for item in items.values():
            yield item
        while len(items) > 0:
            cursor = next(iter(items.keys()))
            items = await self.fetch_items(
                before=self._chunk_size if backward else None,
                after=self._chunk_size if not backward else None,
                cursor=cursor,
            )
            for item in items.values():
                yield item
            items.pop(cursor, None)

    async def size(self) -> int:
        return await self._table.size()

    def add_listener(self, listener: TableListener[T]) -> None:
        self._listeners.append(listener)
        self._listening = True

    def remove_listener(self, listener: TableListener[T]) -> None:
        self._listeners.remove(listener)

    def listen(
        self, callback: AsyncCallback[Mapping[str, T]] | None = None
    ) -> Callable[[], None]:
        self._listening = True
        listener = TableListener(on_cache_update=callback)
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    async def on_add(self, items: Dict[str, bytes]) -> None:
        _items = self._parse_items(items)
        for listener in self._listeners:
            await listener.on_add(_items)

    async def on_update(self, items: Dict[str, bytes]) -> None:
        _items = self._parse_items(items)
        for listener in self._listeners:
            await listener.on_update(_items)

    async def on_remove(self, items: Dict[str, bytes]) -> None:
        _items = self._parse_items(items)
        for listener in self._listeners:
            await listener.on_remove(_items)

    async def on_clear(self) -> None:
        for listener in self._listeners:
            await listener.on_clear()

    async def on_cache_update(self, cache: Dict[str, bytes]) -> None:
        for listener in self._listeners:
            await listener.on_cache_update(self._parse_items(cache))

    def proxy(self, callback: Coro[[T], T | None]) -> Callable[[], None]:
        raise NotImplementedError

    def _parse_items(self, items: Dict[str, bytes]) -> Dict[str, T]:
        parsed: Dict[str, T] = {}
        for key, item in items.items():
            item = self._type.serializer.deserialize(item)
            if not item:
                raise Exception(f"Failed to deserialize item {key}")
            parsed[key] = item
        return parsed
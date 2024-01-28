from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, TypedDict

from omu.client.client import Client
from omu.connection import ConnectionListener
from omu.event.event import JsonEventType, SerializeEventType
from omu.extension.endpoint.endpoint import JsonEndpointType
from omu.extension.extension import Extension, define_extension_type
from omu.interface import Keyable, Serializer

from .model.table_info import TableInfo
from .table import (
    AsyncCallback,
    CallbackTableListener,
    ModelTableType,
    Table,
    TableListener,
    TableType,
)

type Coro[**P, T] = Callable[P, Awaitable[T]]


class TableExtension(Extension):
    def __init__(self, client: Client):
        self._client = client
        self._tables: Dict[str, Table] = {}
        client.events.register(
            TableRegisterEvent,
            TableListenEvent,
            TableProxyListenEvent,
            TableProxyEvent,
            TableItemAddEvent,
            TableItemUpdateEvent,
            TableItemRemoveEvent,
            TableItemClearEvent,
        )
        self.tables = self.get(TablesTableType)

    def register[K: Keyable](self, type: TableType[K, Any]) -> Table[K]:
        if self.has(type):
            raise Exception(f"Table for key {type.info.key()} already registered")
        table = TableImpl(self._client, type, owner=True)
        self._tables[type.info.key()] = table
        return table

    def get[K: Keyable](self, type: TableType[K, Any]) -> Table[K]:
        if self.has(type):
            return self._tables[type.info.key()]
        table = TableImpl(self._client, type)
        self._tables[type.info.key()] = table
        return table

    def has(self, type: TableType[Any, Any]) -> bool:
        return type.info.key() in self._tables


TableExtensionType = define_extension_type(
    "table", lambda client: TableExtension(client), lambda: []
)


class TableEventData(TypedDict):
    type: str


class TableItemsEventData(TypedDict):
    items: Dict[str, Any]
    type: str


class TableProxyEventData(TypedDict):
    items: Dict[str, Any]
    type: str
    key: int


class TableKeysEventData(TypedDict):
    type: str
    items: List[str]


TableRegisterEvent = SerializeEventType.of_extension(
    TableExtensionType, "register", Serializer.model(TableInfo)
)
TableListenEvent = JsonEventType[str].of_extension(TableExtensionType, name="listen")
TableProxyListenEvent = JsonEventType[str].of_extension(
    TableExtensionType, "proxy_listen"
)
TableProxyEvent = JsonEventType[TableProxyEventData].of_extension(
    TableExtensionType, "proxy"
)
TableProxyEndpoint = JsonEndpointType[TableProxyEventData, int].of_extension(
    TableExtensionType,
    "proxy",
)


TableItemAddEvent = JsonEventType[TableItemsEventData].of_extension(
    TableExtensionType, "item_add"
)
TableItemUpdateEvent = JsonEventType[TableItemsEventData].of_extension(
    TableExtensionType, "item_update"
)
TableItemRemoveEvent = JsonEventType[TableItemsEventData].of_extension(
    TableExtensionType, "item_remove"
)
TableItemClearEvent = JsonEventType[TableEventData].of_extension(
    TableExtensionType, "item_clear"
)

TableItemGetEndpoint = JsonEndpointType[
    TableKeysEventData, TableItemsEventData
].of_extension(
    TableExtensionType,
    "item_get",
)


class TableFetchReq(TypedDict):
    type: str
    before: int | None
    after: int | None
    cursor: str | None


TableItemFetchEndpoint = JsonEndpointType[TableFetchReq, Dict[str, Any]].of_extension(
    TableExtensionType, "item_fetch"
)
TableItemSizeEndpoint = JsonEndpointType[TableEventData, int].of_extension(
    TableExtensionType, "item_size"
)
TablesTableType = ModelTableType.of_extension(
    TableExtensionType,
    "tables",
    TableInfo,
)


class TableImpl[T: Keyable](Table[T], ConnectionListener):
    def __init__(self, client: Client, type: TableType[T, Any], owner: bool = False):
        self._client = client
        self._type = type
        self._owner = owner
        self._cache: Dict[str, T] = {}
        self._listeners: List[TableListener[T]] = []
        self._proxies: List[Coro[[T], T | None]] = []
        self.key = type.info.key()
        self._listening = False

        client.events.add_listener(TableProxyEvent, self._on_proxy)
        client.events.add_listener(TableItemAddEvent, self._on_item_add)
        client.events.add_listener(TableItemUpdateEvent, self._on_item_update)
        client.events.add_listener(TableItemRemoveEvent, self._on_item_remove)
        client.events.add_listener(TableItemClearEvent, self._on_item_clear)
        client.connection.add_listener(self)

    @property
    def cache(self) -> Dict[str, T]:
        return self._cache

    async def get(self, key: str) -> T | None:
        if key in self._cache:
            return self._cache[key]
        res = await self._client.endpoints.call(
            TableItemGetEndpoint, TableKeysEventData(type=self.key, items=[key])
        )
        items = self._parse_items(res["items"])
        self._cache.update(items)
        if key in items:
            return items[key]
        return None

    async def add(self, *items: T) -> None:
        data = {item.key(): self._type.serializer.serialize(item) for item in items}
        await self._client.send(
            TableItemAddEvent, TableItemsEventData(type=self.key, items=data)
        )

    async def update(self, *items: T) -> None:
        data = {item.key(): self._type.serializer.serialize(item) for item in items}
        await self._client.send(
            TableItemUpdateEvent, TableItemsEventData(type=self.key, items=data)
        )

    async def remove(self, *items: T) -> None:
        data = {item.key(): self._type.serializer.serialize(item) for item in items}
        await self._client.send(
            TableItemRemoveEvent, TableItemsEventData(type=self.key, items=data)
        )

    async def clear(self) -> None:
        await self._client.send(TableItemClearEvent, TableEventData(type=self.key))

    async def fetch(
        self,
        before: int | None = None,
        after: int | None = None,
        cursor: str | None = None,
    ) -> Dict[str, T]:
        res = await self._client.endpoints.call(
            TableItemFetchEndpoint,
            TableFetchReq(type=self.key, before=before, after=after, cursor=cursor),
        )
        items = self._parse_items(res)
        self._cache.update(items)
        for listener in self._listeners:
            await listener.on_cache_update(self._cache)
        return items

    async def iter(
        self,
        backward: bool = False,
        cursor: str | None = None,
    ) -> AsyncGenerator[T, None]:
        items = await self.fetch(
            before=self._type.info.cache_size if backward else None,
            after=self._type.info.cache_size if not backward else None,
            cursor=cursor,
        )
        for item in items.values():
            yield item
        while len(items) > 0:
            cursor = next(iter(items.keys()))
            items = await self.fetch(
                before=self._type.info.cache_size if backward else None,
                after=self._type.info.cache_size if not backward else None,
                cursor=cursor,
            )
            for item in items.values():
                yield item
            items.pop(cursor, None)

    async def size(self) -> int:
        res = await self._client.endpoints.call(
            TableItemSizeEndpoint, TableEventData(type=self.key)
        )
        return res

    def add_listener(self, listener: TableListener[T]) -> None:
        self._listeners.append(listener)
        self._listening = True

    def remove_listener(self, listener: TableListener[T]) -> None:
        self._listeners.remove(listener)

    def listen(
        self, callback: AsyncCallback[Dict[str, T]] | None = None
    ) -> Callable[[], None]:
        self._listening = True
        listener = CallbackTableListener(on_cache_update=callback)
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def proxy(self, callback: Coro[[T], T | None]) -> Callable[[], None]:
        self._proxies.append(callback)
        return lambda: self._proxies.remove(callback)

    async def on_connected(self) -> None:
        if self._owner:
            await self._client.send(TableRegisterEvent, self._type.info)
        if self._listening:
            await self._client.send(TableListenEvent, self.key)
            if self._type.info.cache_size:
                await self.fetch(self._type.info.cache_size)
        if len(self._proxies) > 0:
            await self._client.send(TableProxyListenEvent, self.key)

    async def _on_proxy(self, event: TableProxyEventData) -> None:
        if event["type"] != self.key:
            return
        items = self._parse_items(event["items"])
        for proxy in self._proxies:
            for key, item in items.items():
                if item := await proxy(item):
                    items[key] = item
                else:
                    del items[key]
        await self._client.endpoints.call(
            TableProxyEndpoint,
            TableProxyEventData(
                type=self.key,
                key=event["key"],
                items={
                    item.key(): self._type.serializer.serialize(item)
                    for item in items.values()
                },
            ),
        )

    async def _on_item_add(self, event: TableItemsEventData) -> None:
        if event["type"] != self.key:
            return
        items = self._parse_items(event["items"])
        self._cache.update(items)
        for listener in self._listeners:
            await listener.on_add(items)
            await listener.on_cache_update(self._cache)

    async def _on_item_update(self, event: TableItemsEventData) -> None:
        if event["type"] != self.key:
            return
        items = self._parse_items(event["items"])
        self._cache.update(items)
        for listener in self._listeners:
            await listener.on_update(items)
            await listener.on_cache_update(self._cache)

    async def _on_item_remove(self, event: TableItemsEventData) -> None:
        if event["type"] != self.key:
            return
        items = self._parse_items(event["items"])
        for key in items.keys():
            if key not in self._cache:
                continue
            del self._cache[key]
        for listener in self._listeners:
            await listener.on_remove(items)
            await listener.on_cache_update(self._cache)

    async def _on_item_clear(self, event: TableEventData) -> None:
        if event["type"] != self.key:
            return
        self._cache.clear()
        for listener in self._listeners:
            await listener.on_clear()
            await listener.on_cache_update(self._cache)

    def _parse_items(self, items: Dict[str, Any]) -> Dict[str, T]:
        parsed: Dict[str, T] = {}
        for key, item in items.items():
            item = self._type.serializer.deserialize(item)
            if not item:
                raise Exception(f"Failed to deserialize item {key}")
            parsed[key] = item
        return parsed

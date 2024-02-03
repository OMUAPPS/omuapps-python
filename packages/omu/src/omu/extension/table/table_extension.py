from typing import AsyncGenerator, Awaitable, Callable, Dict, List, Mapping, TypedDict

from omu.client.client import Client
from omu.connection import ConnectionListener
from omu.event.event import JsonEventType, SerializeEventType
from omu.extension.endpoint.endpoint import JsonEndpointType, SerializeEndpointType
from omu.extension.extension import Extension, define_extension_type
from omu.helper import ByteReader, ByteWriter
from omu.interface import Keyable, Serializer
from omu.interface.serializable import Serializable

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

    def register[K: Keyable](self, type: TableType[K]) -> Table[K]:
        if self.has(type):
            raise Exception(f"Table for key {type.info.key()} already registered")
        table = TableImpl(self._client, type, owner=True)
        self._tables[type.info.key()] = table
        return table

    def get[K: Keyable](self, type: TableType[K]) -> Table[K]:
        if self.has(type):
            return self._tables[type.info.key()]
        table = TableImpl(self._client, type)
        self._tables[type.info.key()] = table
        return table

    def has(self, type: TableType) -> bool:
        return type.info.key() in self._tables


TableExtensionType = define_extension_type(
    "table", lambda client: TableExtension(client), lambda: []
)


class TableEventData(TypedDict):
    type: str


class TableItemsData(TableEventData):
    items: Dict[str, bytes]


class TableKeysData(TableEventData):
    keys: List[str]


class TableProxyData(TableItemsData):
    key: int


class TableItemsSerielizer(Serializable[TableItemsData, bytes]):
    def serialize(self, item: TableItemsData) -> bytes:
        writer = ByteWriter()
        writer.write_string(item["type"])
        writer.write_int(len(item["items"]))
        for key, value in item["items"].items():
            writer.write_string(key)
            writer.write_byte_array(value)
        return writer.finish()

    def deserialize(self, data: bytes) -> TableItemsData:
        reader = ByteReader(data)
        type = reader.read_string()
        item_count = reader.read_int()
        items = {}
        for _ in range(item_count):
            key = reader.read_string()
            value = reader.read_byte_array()
            items[key] = value
        reader.finish()
        return {"type": type, "items": items}


class TableProxySerielizer(Serializable[TableProxyData, bytes]):
    def serialize(self, item: TableProxyData) -> bytes:
        writer = ByteWriter()
        writer.write_string(item["type"])
        writer.write_int(item["key"])
        writer.write_int(len(item["items"]))
        for key, value in item["items"].items():
            writer.write_string(key)
            writer.write_byte_array(value)
        return writer.finish()

    def deserialize(self, data: bytes) -> TableProxyData:
        reader = ByteReader(data)
        type = reader.read_string()
        key = reader.read_int()
        item_count = reader.read_int()
        items = {}
        for _ in range(item_count):
            item_key = reader.read_string()
            value = reader.read_byte_array()
            items[item_key] = value
        reader.finish()
        return {"type": type, "key": key, "items": items}


TableRegisterEvent = JsonEventType.of_extension(
    TableExtensionType, "register", Serializer.model(TableInfo)
)
TableListenEvent = JsonEventType[str].of_extension(TableExtensionType, name="listen")
TableProxyListenEvent = JsonEventType[str].of_extension(
    TableExtensionType, "proxy_listen"
)
TableProxyEvent = SerializeEventType[TableProxyData].of_extension(
    TableExtensionType,
    "proxy",
    serializer=TableProxySerielizer(),
)
TableProxyEndpoint = SerializeEndpointType[TableProxyData, int].of_extension(
    TableExtensionType,
    "proxy",
    request_serializer=TableProxySerielizer(),
    response_serializer=Serializer.json(),
)


TableItemAddEvent = SerializeEventType[TableItemsData].of_extension(
    TableExtensionType, "item_add", TableItemsSerielizer()
)
TableItemUpdateEvent = SerializeEventType[TableItemsData].of_extension(
    TableExtensionType, "item_update", TableItemsSerielizer()
)
TableItemRemoveEvent = SerializeEventType[TableItemsData].of_extension(
    TableExtensionType, "item_remove", TableItemsSerielizer()
)
TableItemClearEvent = JsonEventType[TableEventData].of_extension(
    TableExtensionType, "item_clear"
)


TableItemGetEndpoint = SerializeEndpointType[
    TableKeysData, TableItemsData
].of_extension(
    TableExtensionType,
    "item_get",
    request_serializer=Serializer.json(),
    response_serializer=TableItemsSerielizer(),
)


class TableFetchReq(TypedDict):
    type: str
    before: int | None
    after: int | None
    cursor: str | None


TableItemFetchEndpoint = SerializeEndpointType[
    TableFetchReq, TableItemsData
].of_extension(
    TableExtensionType,
    "item_fetch",
    request_serializer=Serializer.json(),
    response_serializer=TableItemsSerielizer(),
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
    def __init__(self, client: Client, type: TableType[T], owner: bool = False):
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
            TableItemGetEndpoint, TableKeysData(type=self.key, keys=[key])
        )
        items = self._parse_items(res["items"])
        self._cache.update(items)
        if key in items:
            return items[key]
        return None

    async def add(self, *items: T) -> None:
        data = {item.key(): self._type.serializer.serialize(item) for item in items}
        await self._client.send(
            TableItemAddEvent, TableItemsData(type=self.key, items=data)
        )

    async def update(self, *items: T) -> None:
        data = {item.key(): self._type.serializer.serialize(item) for item in items}
        await self._client.send(
            TableItemUpdateEvent, TableItemsData(type=self.key, items=data)
        )

    async def remove(self, *items: T) -> None:
        data = {item.key(): self._type.serializer.serialize(item) for item in items}
        await self._client.send(
            TableItemRemoveEvent, TableItemsData(type=self.key, items=data)
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
        items = self._parse_items(res["items"])
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
        self, callback: AsyncCallback[Mapping[str, T]] | None = None
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
        if len(self._proxies) > 0:
            await self._client.send(TableProxyListenEvent, self.key)

    async def _on_proxy(self, event: TableProxyData) -> None:
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
            TableProxyData(
                type=self.key,
                key=event["key"],
                items={
                    item.key(): self._type.serializer.serialize(item)
                    for item in items.values()
                },
            ),
        )

    async def _on_item_add(self, event: TableItemsData) -> None:
        if event["type"] != self.key:
            return
        items = self._parse_items(event["items"])
        self._cache.update(items)
        for listener in self._listeners:
            await listener.on_add(items)
            await listener.on_cache_update(self._cache)

    async def _on_item_update(self, event: TableItemsData) -> None:
        if event["type"] != self.key:
            return
        items = self._parse_items(event["items"])
        self._cache.update(items)
        for listener in self._listeners:
            await listener.on_update(items)
            await listener.on_cache_update(self._cache)

    async def _on_item_remove(self, event: TableItemsData) -> None:
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

    def _parse_items(self, items: Dict[str, bytes]) -> Dict[str, T]:
        parsed: Dict[str, T] = {}
        for key, item in items.items():
            item = self._type.serializer.deserialize(item)
            if not item:
                raise Exception(f"Failed to deserialize item {key}")
            parsed[key] = item
        return parsed

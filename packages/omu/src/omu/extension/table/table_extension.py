from typing import (
    AsyncGenerator,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    TypedDict,
)

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.endpoint import EndpointType
from omu.helper import AsyncCallback, Coro
from omu.identifier import Identifier
from omu.interface import Keyable
from omu.network.bytebuffer import ByteReader, ByteWriter
from omu.network.packet import PacketType
from omu.serializer import JsonSerializable, Serializable, Serializer

from .table import (
    Table,
    TableConfig,
    TableListeners,
    TableType,
)

type ModelType[T: Keyable, D] = JsonSerializable[T, D]


class TableExtension(Extension):
    def __init__(self, client: Client):
        self._client = client
        self._tables: Dict[Identifier, Table] = {}
        client.network.register_packet(
            TableConfigSetEvent,
            TableListenEvent,
            TableProxyListenEvent,
            TableProxyEvent,
            TableItemAddEvent,
            TableItemUpdateEvent,
            TableItemRemoveEvent,
            TableItemClearEvent,
        )

    def create[T](
        self,
        identifier: Identifier,
        serializer: Serializable[T, bytes],
        key_function: Callable[[T], str],
    ) -> Table[T]:
        if self.has(identifier):
            raise ValueError(f"Table with identifier {identifier} already exists")
        table = TableImpl(
            self._client,
            identifier=identifier,
            serializer=serializer,
            key_function=key_function,
        )
        self._tables[identifier] = table
        return table

    def get[T](self, type: TableType[T]) -> Table[T]:
        if self.has(type.identifier):
            return self._tables[type.identifier]
        return self.create(type.identifier, type.serializer, type.key_func)

    def model[T: Keyable, D](
        self, identifier: Identifier, name: str, type: type[ModelType[T, D]]
    ) -> Table[T]:
        identifier = identifier / name
        if self.has(identifier):
            return self._tables[identifier]
        return self.create(
            identifier,
            Serializer.model(type).pipe(Serializer.json()),
            lambda item: item.key(),
        )

    def has(self, identifier: Identifier) -> bool:
        return identifier in self._tables


TableExtensionType = ExtensionType(
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
        with ByteReader(data) as reader:
            type = reader.read_string()
            item_count = reader.read_int()
            items: Dict[str, bytes] = {}
            for _ in range(item_count):
                key = reader.read_string()
                value = reader.read_byte_array()
                items[key] = value
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
        with ByteReader(data) as reader:
            type = reader.read_string()
            key = reader.read_int()
            item_count = reader.read_int()
            items: Dict[str, bytes] = {}
            for _ in range(item_count):
                item_key = reader.read_string()
                value = reader.read_byte_array()
                items[item_key] = value
        return {"type": type, "key": key, "items": items}


class SetConfigReq(TypedDict):
    type: str
    config: TableConfig


TableConfigSetEvent = PacketType[SetConfigReq].create_json(
    TableExtensionType, "config_set"
)
TableListenEvent = PacketType[str].create_json(TableExtensionType, name="listen")
TableProxyListenEvent = PacketType[str].create_json(TableExtensionType, "proxy_listen")
TableProxyEvent = PacketType[TableProxyData].create_serialized(
    TableExtensionType,
    "proxy",
    serializer=TableProxySerielizer(),
)
TableProxyEndpoint = EndpointType[TableProxyData, int].create_serialized(
    TableExtensionType,
    "proxy",
    request_serializer=TableProxySerielizer(),
    response_serializer=Serializer.json(),
)


TableItemAddEvent = PacketType[TableItemsData].create_serialized(
    TableExtensionType, "item_add", TableItemsSerielizer()
)
TableItemUpdateEvent = PacketType[TableItemsData].create_serialized(
    TableExtensionType, "item_update", TableItemsSerielizer()
)
TableItemRemoveEvent = PacketType[TableItemsData].create_serialized(
    TableExtensionType, "item_remove", TableItemsSerielizer()
)
TableItemClearEvent = PacketType[TableEventData].create_json(
    TableExtensionType, "item_clear"
)


TableItemGetEndpoint = EndpointType[TableKeysData, TableItemsData].create_serialized(
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


TableItemFetchEndpoint = EndpointType[TableFetchReq, TableItemsData].create_serialized(
    TableExtensionType,
    "item_fetch",
    request_serializer=Serializer.json(),
    response_serializer=TableItemsSerielizer(),
)
TableItemFetchAllEndpoint = EndpointType[
    TableEventData, TableItemsData
].create_serialized(
    TableExtensionType,
    "item_fetch_all",
    request_serializer=Serializer.json(),
    response_serializer=TableItemsSerielizer(),
)
TableItemSizeEndpoint = EndpointType[TableEventData, int].create_json(
    TableExtensionType, "item_size"
)


class TableImpl[T](Table[T]):
    def __init__(
        self,
        client: Client,
        identifier: Identifier,
        serializer: Serializable[T, bytes],
        key_function: Callable[[T], str],
    ):
        self._client = client
        self._identifier = identifier
        self._serializer = serializer
        self._key_function = key_function
        self._cache: Dict[str, T] = {}
        self._listeners = TableListeners[T]()
        self._proxies: List[Coro[[T], T | None]] = []
        self._chunk_size = 100
        self._cache_size: int | None = None
        self._listening = False
        self._config: TableConfig | None = None
        self.key = identifier.key()

        client.network.add_packet_handler(TableProxyEvent, self._on_proxy)
        client.network.add_packet_handler(TableItemAddEvent, self._on_item_add)
        client.network.add_packet_handler(TableItemUpdateEvent, self._on_item_update)
        client.network.add_packet_handler(TableItemRemoveEvent, self._on_item_remove)
        client.network.add_packet_handler(TableItemClearEvent, self._on_item_clear)
        client.network.add_task(self.on_connected)

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
        data = self._serialize_items(items)
        await self._client.send(
            TableItemAddEvent, TableItemsData(type=self.key, items=data)
        )

    async def update(self, *items: T) -> None:
        data = self._serialize_items(items)
        await self._client.send(
            TableItemUpdateEvent, TableItemsData(type=self.key, items=data)
        )

    async def remove(self, *items: T) -> None:
        data = self._serialize_items(items)
        await self._client.send(
            TableItemRemoveEvent, TableItemsData(type=self.key, items=data)
        )

    async def clear(self) -> None:
        await self._client.send(TableItemClearEvent, TableEventData(type=self.key))

    async def fetch_items(
        self,
        before: int | None = None,
        after: int | None = None,
        cursor: str | None = None,
    ) -> Dict[str, T]:
        items_response = await self._client.endpoints.call(
            TableItemFetchEndpoint,
            TableFetchReq(type=self.key, before=before, after=after, cursor=cursor),
        )
        items = self._parse_items(items_response["items"])
        await self.update_cache(items)
        return items

    async def fetch_all(self) -> Dict[str, T]:
        items_response = await self._client.endpoints.call(
            TableItemFetchAllEndpoint, TableEventData(type=self.key)
        )
        items = self._parse_items(items_response["items"])
        await self.update_cache(items)
        return items

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
        res = await self._client.endpoints.call(
            TableItemSizeEndpoint, TableEventData(type=self.key)
        )
        return res

    def listen(
        self, callback: AsyncCallback[Mapping[str, T]] | None = None
    ) -> Callable[[], None]:
        self._listening = True
        if callback is not None:
            self._listeners.cache_update += callback
            return lambda: self._listeners.cache_update.unsubscribe(callback)
        return lambda: None

    def proxy(self, callback: Coro[[T], T | None]) -> Callable[[], None]:
        self._proxies.append(callback)
        return lambda: self._proxies.remove(callback)

    def set_config(self, config: TableConfig) -> None:
        self._config = config

    async def on_connected(self) -> None:
        if self._config is not None:
            await self._client.send(
                TableConfigSetEvent, SetConfigReq(type=self.key, config=self._config)
            )
        if self._listening:
            await self._client.send(TableListenEvent, self.key)
        if len(self._proxies) > 0:
            await self._client.send(TableProxyListenEvent, self.key)

    async def _on_proxy(self, event: TableProxyData) -> None:
        if event["type"] != self.key:
            return
        items = self._parse_items(event["items"])
        for proxy in self._proxies:
            for key, item in list(items.items()):
                updated_item = await proxy(item)
                if updated_item is None:
                    del items[key]
                else:
                    items[key] = updated_item
        serialized_items = self._serialize_items(items.values())
        await self._client.endpoints.call(
            TableProxyEndpoint,
            TableProxyData(
                type=self.key,
                key=event["key"],
                items=serialized_items,
            ),
        )

    async def _on_item_add(self, event: TableItemsData) -> None:
        if event["type"] != self.key:
            return
        items = self._parse_items(event["items"])
        await self._listeners.add(items)
        await self.update_cache(items)

    async def _on_item_update(self, event: TableItemsData) -> None:
        if event["type"] != self.key:
            return
        items = self._parse_items(event["items"])
        await self._listeners.update(items)
        await self.update_cache(items)

    async def _on_item_remove(self, event: TableItemsData) -> None:
        if event["type"] != self.key:
            return
        items = self._parse_items(event["items"])
        await self._listeners.remove(items)
        for key in items.keys():
            if key not in self._cache:
                continue
            del self._cache[key]
        await self._listeners.cache_update(self._cache)

    async def _on_item_clear(self, event: TableEventData) -> None:
        if event["type"] != self.key:
            return
        await self._listeners.clear()
        self._cache.clear()
        await self._listeners.cache_update(self._cache)

    async def update_cache(self, items: Dict[str, T]) -> None:
        if self._cache_size is None:
            self._cache = items
        else:
            merged_cache = dict(**self._cache, **items).items()
            cache_array = tuple(merged_cache)
            self._cache = dict(cache_array[: self._cache_size])
        await self._listeners.cache_update(self._cache)

    def _parse_items(self, items: Dict[str, bytes]) -> Dict[str, T]:
        parsed_items: Dict[str, T] = {}
        for key, item_bytes in items.items():
            item = self._serializer.deserialize(item_bytes)
            if item is None:
                raise ValueError(f"Failed to deserialize item with key: {key}")
            parsed_items[key] = item
        return parsed_items

    def _serialize_items(self, items: Iterable[T]) -> Dict[str, bytes]:
        serialized_items: Dict[str, bytes] = {}
        for item in items:
            key = self._key_function(item)
            serialized_items[key] = self._serializer.serialize(item)
        return serialized_items

    def set_cache_size(self, size: int | None) -> None:
        self._cache_size = size

    @property
    def listeners(self) -> TableListeners[T]:
        return self._listeners

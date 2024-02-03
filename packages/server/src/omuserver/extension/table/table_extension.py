from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from loguru import logger
from omu.extension.table import Table, TableType
from omu.extension.table.model.table_info import TableInfo
from omu.extension.table.table_extension import (
    TableEventData,
    TableFetchReq,
    TableItemAddEvent,
    TableItemClearEvent,
    TableItemFetchEndpoint,
    TableItemGetEndpoint,
    TableItemRemoveEvent,
    TableItemsData,
    TableItemSizeEndpoint,
    TableItemUpdateEvent,
    TableKeysData,
    TableListenEvent,
    TableProxyData,
    TableProxyEndpoint,
    TableProxyEvent,
    TableProxyListenEvent,
    TableRegisterEvent,
)
from omu.identifier import Identifier
from omu.interface import Keyable

from omuserver.extension import Extension
from omuserver.extension.table.serialized_table import SerializedTable
from omuserver.server import Server, ServerListener
from omuserver.session import Session

from .adapters.sqlitetable import SqliteTableAdapter
from .adapters.tableadapter import TableAdapter
from .cached_table import CachedTable
from .server_table import ServerTable


class TableExtension(Extension, ServerListener):
    def __init__(self, server: Server) -> None:
        self._server = server
        self._tables: Dict[str, ServerTable] = {}
        self._adapters: List[TableAdapter] = []
        server.events.register(
            TableRegisterEvent,
            TableListenEvent,
            TableProxyListenEvent,
            TableProxyEvent,
            TableItemAddEvent,
            TableItemUpdateEvent,
            TableItemRemoveEvent,
            TableItemClearEvent,
        )
        server.events.add_listener(TableRegisterEvent, self._on_table_register)
        server.events.add_listener(TableListenEvent, self._on_table_listen)
        server.events.add_listener(TableProxyListenEvent, self._on_table_proxy_listen)
        server.events.add_listener(TableItemAddEvent, self._on_table_item_add)
        server.events.add_listener(TableItemUpdateEvent, self._on_table_item_update)
        server.events.add_listener(TableItemRemoveEvent, self._on_table_item_remove)
        server.events.add_listener(TableItemClearEvent, self._on_table_item_clear)
        server.endpoints.bind_endpoint(TableItemGetEndpoint, self._on_table_item_get)
        server.endpoints.bind_endpoint(
            TableItemFetchEndpoint, self._on_table_item_fetch
        )
        server.endpoints.bind_endpoint(TableItemSizeEndpoint, self._on_table_item_size)
        server.endpoints.bind_endpoint(TableProxyEndpoint, self._on_table_proxy)
        server.add_listener(self)

    @classmethod
    def create(cls, server: Server) -> TableExtension:
        return cls(server)

    async def _on_table_item_get(
        self, session: Session, req: TableKeysData
    ) -> TableItemsData:
        table = await self.get_table(req["type"])
        items = await table.get_all(req["keys"])
        return TableItemsData(
            type=req["type"],
            items=items,
        )

    async def _on_table_item_fetch(
        self, session: Session, req: TableFetchReq
    ) -> TableItemsData:
        table = await self.get_table(req["type"])
        items = await table.fetch(
            before=req.get("before", None),
            after=req.get("after", None),
            cursor=req.get("cursor", None),
        )
        return TableItemsData(
            type=req["type"],
            items=items,
        )

    async def _on_table_item_size(self, session: Session, req: TableEventData) -> int:
        table = await self.get_table(req["type"])
        return await table.size()

    async def _on_table_register(self, session: Session, info: TableInfo) -> None:
        if info.key() in self._tables:
            logger.warning(f"Skipping table {info.key()} already registered")
            return
        path = self.get_table_path(info.identifier)
        adapter = SqliteTableAdapter.create(path)
        await adapter.load()
        table = CachedTable(self._server, info.key())
        table.set_adapter(adapter)
        table.cache_size = info.cache_size
        self._tables[info.key()] = table

    async def _on_table_listen(self, session: Session, type: str) -> None:
        table = await self.get_table(type)
        table.attach_session(session)

    async def _on_table_proxy_listen(self, session: Session, type: str) -> None:
        table = await self.get_table(type)
        table.attach_proxy_session(session)

    async def _on_table_proxy(self, session: Session, event: TableProxyData) -> int:
        table = await self.get_table(event["type"])
        key = await table.proxy(session, event["key"], event["items"])
        return key

    async def _on_table_item_add(self, session: Session, event: TableItemsData) -> None:
        table = await self.get_table(event["type"])
        await table.add(event["items"])

    async def _on_table_item_update(
        self, session: Session, event: TableItemsData
    ) -> None:
        table = await self.get_table(event["type"])
        await table.update(event["items"])

    async def _on_table_item_remove(
        self, session: Session, event: TableItemsData
    ) -> None:
        table = await self.get_table(event["type"])
        await table.remove(list(event["items"].keys()))

    async def _on_table_item_clear(
        self, session: Session, event: TableEventData
    ) -> None:
        table = await self.get_table(event["type"])
        await table.clear()

    def create_table(self, info: TableInfo):
        path = self.get_table_path(info.identifier)
        table = CachedTable(self._server, info.key())
        adapter = SqliteTableAdapter.create(path)
        table.set_adapter(adapter)
        table.cache_size = info.cache_size
        self._tables[info.key()] = table
        return table

    def register_table[T: Keyable](self, table_type: TableType[T]) -> Table[T]:
        if table_type.info.key() in self._tables:
            raise Exception(f"Table {table_type.info.key()} already registered")
        table = self.create_table(table_type.info)
        return SerializedTable(table, table_type)

    async def get_table(self, key: str) -> ServerTable:
        if key in self._tables:
            return self._tables[key]
        table = CachedTable(self._server, key)
        adapter = SqliteTableAdapter.create(
            self.get_table_path(Identifier.from_key(key))
        )
        table.set_adapter(adapter)
        self._tables[key] = table
        return table

    def get_table_path(self, id: Identifier) -> Path:
        path = self._server.directories.get("tables") / id.namespace / id.name
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def on_start(self) -> None:
        for table in self._tables.values():
            if table.adapter is None:
                continue
            await table.adapter.load()

    async def on_shutdown(self) -> None:
        for table in self._tables.values():
            await table.store()

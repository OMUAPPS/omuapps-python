from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from loguru import logger
from omu.extension.table.model.table_info import TableInfo
from omu.extension.table.table_extension import (
    TableEventData,
    TableFetchReq,
    TableItemAddEvent,
    TableItemClearEvent,
    TableItemFetchEndpoint,
    TableItemGetEndpoint,
    TableItemRemoveEvent,
    TableItemsEventData,
    TableItemSizeEndpoint,
    TableItemUpdateEvent,
    TableKeysEventData,
    TableListenEvent,
    TableProxyEndpoint,
    TableProxyEvent,
    TableProxyEventData,
    TableProxyListenEvent,
    TableRegisterEvent,
    TableType,
)
from omu.interface import Keyable, Serializer

from omuserver.extension import Extension
from omuserver.server import Server, ServerListener
from omuserver.session import Session

from .adapters import DictTableAdapter, SqliteTableAdapter
from .cached_table import CachedTable
from .server_table import ServerTable


class TableExtension(Extension, ServerListener):
    def __init__(self, server: Server) -> None:
        self._server = server
        self._tables: Dict[str, ServerTable] = {}
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
        self, session: Session, req: TableKeysEventData
    ) -> TableItemsEventData:
        table = self._tables.get(req["type"], None)
        if table is None:
            return TableItemsEventData(type=req["type"], items={})
        items = await table.get_all(req["items"])
        return TableItemsEventData(
            type=req["type"],
            items={
                key: table.serializer.serialize(item) for key, item in items.items()
            },
        )

    async def _on_table_item_fetch(
        self, session: Session, req: TableFetchReq
    ) -> Dict[str, Any]:
        table = self._tables.get(req["type"], None)
        if table is None:
            return {}
        items = await table.fetch(
            before=req.get("before", None),
            after=req.get("after", None),
            cursor=req.get("cursor", None),
        )
        return {key: table.serializer.serialize(item) for key, item in items.items()}

    async def _on_table_item_size(self, session: Session, req: TableEventData) -> int:
        table = self._tables.get(req["type"], None)
        if table is None:
            return 0
        return await table.size()

    async def _on_table_register(self, session: Session, info: TableInfo) -> None:
        if info.key() in self._tables:
            logger.warning(f"Skipping table {info.key()} already registered")
            return
        table = self.create_table(info, Serializer.noop())
        await table.load()

    async def _on_table_listen(self, session: Session, type: str) -> None:
        table = self._tables.get(type, None)
        if table is None:
            return
        table.attach_session(session)

    async def _on_table_proxy_listen(self, session: Session, type: str) -> None:
        table = self._tables.get(type, None)
        if table is None:
            return
        table.attach_proxy_session(session)

    async def _on_table_proxy(
        self, session: Session, event: TableProxyEventData
    ) -> int:
        table = self._tables.get(event["type"], None)
        if table is None:
            return 0
        key = await table.proxy(session, event["key"], event["items"])
        return key

    async def _on_table_item_add(
        self, session: Session, event: TableItemsEventData
    ) -> None:
        table = self._tables.get(event["type"], None)
        if table is None:
            return
        await table.add(event["items"])

    async def _on_table_item_update(
        self, session: Session, event: TableItemsEventData
    ) -> None:
        table = self._tables.get(event["type"], None)
        if table is None:
            return
        await table.update(event["items"])

    async def _on_table_item_remove(
        self, session: Session, event: TableItemsEventData
    ) -> None:
        table = self._tables.get(event["type"], None)
        if table is None:
            return
        await table.remove(list(event["items"].keys()))

    async def _on_table_item_clear(
        self, session: Session, event: TableEventData
    ) -> None:
        table = self._tables.get(event["type"], None)
        if table is None:
            return
        await table.clear()

    def create_table(self, info, serializer):
        path = self.get_table_path(info)
        if info.use_database:
            table = SqliteTableAdapter.create(path)
        else:
            table = DictTableAdapter.create(path)
        server_table = CachedTable(self._server, info, serializer, table)
        self._tables[info.key()] = server_table
        return server_table

    def register_table[T: Keyable, D](
        self, table_type: TableType[T, Any]
    ) -> ServerTable[T]:
        if table_type.info.key() in self._tables:
            raise Exception(f"Table {table_type.info.key()} already registered")
        table = self.create_table(table_type.info, table_type.serializer)
        return table

    def get_table_path(self, info: TableInfo) -> Path:
        path = self._server.directories.get("tables") / info.owner / info.name
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def on_start(self) -> None:
        for table in self._tables.values():
            await table.load()

    async def on_shutdown(self) -> None:
        for table in self._tables.values():
            await table.store()

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from omu.extension.table import Table, TableType
from omu.extension.table.table_extension import (
    TABLE_CONFIG_SET_PACKET,
    TABLE_ITEM_ADD_PACKET,
    TABLE_ITEM_CLEAR_PACKET,
    TABLE_ITEM_FETCH_ALL_ENDPOINT,
    TABLE_ITEM_FETCH_ENDPOINT,
    TABLE_ITEM_GET_ENDPOINT,
    TABLE_ITEM_REMOVE_EVENT,
    TABLE_ITEM_SIZE_ENDPOINT,
    TABLE_ITEM_UPDATE_PACKET,
    TABLE_LISTEN_PACKET,
    TABLE_PROXY_ENDPOINT,
    TABLE_PROXY_LISTEN_PACKET,
    TABLE_PROXY_PACKET,
    SetConfigReq,
    TableEventData,
    TableFetchReq,
    TableItemsData,
    TableKeysData,
    TableProxyData,
)
from omu.identifier import Identifier
from omu.interface import Keyable

from omuserver.extension.table.serialized_table import SerializedTable
from omuserver.server import Server
from omuserver.session import Session

from .adapters.sqlitetable import SqliteTableAdapter
from .adapters.tableadapter import TableAdapter
from .cached_table import CachedTable
from .server_table import ServerTable


class TableExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        self._tables: Dict[Identifier, ServerTable] = {}
        self._adapters: List[TableAdapter] = []
        server.packet_dispatcher.register(
            TABLE_CONFIG_SET_PACKET,
            TABLE_LISTEN_PACKET,
            TABLE_PROXY_LISTEN_PACKET,
            TABLE_PROXY_PACKET,
            TABLE_ITEM_ADD_PACKET,
            TABLE_ITEM_UPDATE_PACKET,
            TABLE_ITEM_REMOVE_EVENT,
            TABLE_ITEM_CLEAR_PACKET,
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_CONFIG_SET_PACKET, self._on_table_set_config
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_LISTEN_PACKET, self._on_table_listen
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_PROXY_LISTEN_PACKET, self._on_table_proxy_listen
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_ADD_PACKET, self._on_table_item_add
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_UPDATE_PACKET, self._on_table_item_update
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_REMOVE_EVENT, self._on_table_item_remove
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_CLEAR_PACKET, self._on_table_item_clear
        )
        server.endpoints.bind_endpoint(TABLE_ITEM_GET_ENDPOINT, self._on_table_item_get)
        server.endpoints.bind_endpoint(
            TABLE_ITEM_FETCH_ENDPOINT, self._on_table_item_fetch
        )
        server.endpoints.bind_endpoint(
            TABLE_ITEM_FETCH_ALL_ENDPOINT, self._on_table_item_fetch_all
        )
        server.endpoints.bind_endpoint(
            TABLE_ITEM_SIZE_ENDPOINT, self._on_table_item_size
        )
        server.endpoints.bind_endpoint(TABLE_PROXY_ENDPOINT, self._on_table_proxy)
        server.listeners.stop += self.on_server_stop

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
        items = await table.fetch_items(
            before=req.get("before"),
            after=req.get("after"),
            cursor=req.get("cursor"),
        )
        return TableItemsData(
            type=req["type"],
            items=items,
        )

    async def _on_table_item_fetch_all(
        self, session: Session, req: TableEventData
    ) -> TableItemsData:
        table = await self.get_table(req["type"])
        items = await table.fetch_all()
        return TableItemsData(
            type=req["type"],
            items=items,
        )

    async def _on_table_item_size(self, session: Session, req: TableEventData) -> int:
        table = await self.get_table(req["type"])
        return await table.size()

    async def _on_table_set_config(
        self, session: Session, config: SetConfigReq
    ) -> None:
        table = await self.get_table(config["type"])
        table.set_config(config["config"])

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

    async def register_table[T: Keyable](self, table_type: TableType[T]) -> Table[T]:
        table = await self.get_table(table_type.identifier.key())
        return SerializedTable(table, table_type)

    async def get_table(self, id: str) -> ServerTable:
        identifier = Identifier.from_key(id)
        if identifier in self._tables:
            return self._tables[identifier]
        table = CachedTable(self._server, identifier)
        adapter = SqliteTableAdapter.create(self.get_table_path(identifier))
        await adapter.load()
        table.set_adapter(adapter)
        self._tables[identifier] = table
        return table

    def get_table_path(self, identifier: Identifier) -> Path:
        path = self._server.directories.get("tables") / identifier.to_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def on_server_stop(self) -> None:
        for table in self._tables.values():
            await table.store()

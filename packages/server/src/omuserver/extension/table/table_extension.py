from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from omu.extension.table import Table, TableType
from omu.extension.table.table_extension import (
    TABLE_BIND_PERMISSION_PACKET,
    TABLE_CONFIG_PACKET,
    TABLE_FETCH_ALL_ENDPOINT,
    TABLE_FETCH_ENDPOINT,
    TABLE_ITEM_ADD_PACKET,
    TABLE_ITEM_CLEAR_PACKET,
    TABLE_ITEM_GET_ENDPOINT,
    TABLE_ITEM_REMOVE_PACKET,
    TABLE_ITEM_UPDATE_PACKET,
    TABLE_LISTEN_PACKET,
    TABLE_PROXY_LISTEN_PACKET,
    TABLE_PROXY_PACKET,
    TABLE_SIZE_ENDPOINT,
    BindPermissionPacket,
    SetConfigPacket,
    TableFetchPacket,
    TableItemsPacket,
    TableKeysPacket,
    TablePacket,
    TableProxyPacket,
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
            TABLE_BIND_PERMISSION_PACKET,
            TABLE_CONFIG_PACKET,
            TABLE_LISTEN_PACKET,
            TABLE_PROXY_LISTEN_PACKET,
            TABLE_PROXY_PACKET,
            TABLE_ITEM_ADD_PACKET,
            TABLE_ITEM_UPDATE_PACKET,
            TABLE_ITEM_REMOVE_PACKET,
            TABLE_ITEM_CLEAR_PACKET,
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_BIND_PERMISSION_PACKET,
            self._on_table_set_permission,
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_CONFIG_PACKET, self._on_table_set_config
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_LISTEN_PACKET, self._on_table_listen
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_PROXY_LISTEN_PACKET, self._on_table_proxy_listen
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_PROXY_PACKET, self._on_table_proxy
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_ADD_PACKET, self._on_table_item_add
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_UPDATE_PACKET, self._on_table_item_update
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_REMOVE_PACKET, self._on_table_item_remove
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_CLEAR_PACKET, self._on_table_item_clear
        )
        server.endpoints.bind_endpoint(TABLE_ITEM_GET_ENDPOINT, self._on_table_item_get)
        server.endpoints.bind_endpoint(TABLE_FETCH_ENDPOINT, self._on_table_item_fetch)
        server.endpoints.bind_endpoint(
            TABLE_FETCH_ALL_ENDPOINT, self._on_table_item_fetch_all
        )
        server.endpoints.bind_endpoint(TABLE_SIZE_ENDPOINT, self._on_table_item_size)
        server.listeners.stop += self.on_server_stop

    async def _on_table_item_get(
        self, session: Session, packet: TableKeysPacket
    ) -> TableItemsPacket:
        table = await self.get_table(packet.id)
        items = await table.get_many(*packet.keys)
        return TableItemsPacket(
            id=packet.id,
            items=items,
        )

    async def _on_table_item_fetch(
        self, session: Session, packet: TableFetchPacket
    ) -> TableItemsPacket:
        table = await self.get_table(packet.id)
        items = await table.fetch_items(
            before=packet.before,
            after=packet.after,
            cursor=packet.cursor,
        )
        return TableItemsPacket(
            id=packet.id,
            items=items,
        )

    async def _on_table_item_fetch_all(
        self, session: Session, req: TablePacket
    ) -> TableItemsPacket:
        table = await self.get_table(req.id)
        items = await table.fetch_all()
        return TableItemsPacket(
            id=req.id,
            items=items,
        )

    async def _on_table_item_size(self, session: Session, packet: TablePacket) -> int:
        table = await self.get_table(packet.id)
        return await table.size()

    async def _on_table_set_permission(
        self, session: Session, permission: BindPermissionPacket
    ) -> None:
        table = await self.get_table(permission.id)
        table.bind_permission(permission.permission)

    async def _on_table_set_config(
        self, session: Session, config: SetConfigPacket
    ) -> None:
        table = await self.get_table(config.id)
        table.set_config(config.config)

    async def _on_table_listen(self, session: Session, id: Identifier) -> None:
        table = await self.get_table(id)
        table.attach_session(session)

    async def _on_table_proxy_listen(self, session: Session, id: Identifier) -> None:
        table = await self.get_table(id)
        table.attach_proxy_session(session)

    async def _on_table_proxy(self, session: Session, packet: TableProxyPacket) -> None:
        table = await self.get_table(packet.id)
        await table.proxy(session, packet.key, packet.items)

    async def _on_table_item_add(
        self, session: Session, packet: TableItemsPacket
    ) -> None:
        table = await self.get_table(packet.id)
        await table.add(packet.items)

    async def _on_table_item_update(
        self, session: Session, packet: TableItemsPacket
    ) -> None:
        table = await self.get_table(packet.id)
        await table.update(packet.items)

    async def _on_table_item_remove(
        self, session: Session, packet: TableItemsPacket
    ) -> None:
        table = await self.get_table(packet.id)
        await table.remove(list(packet.items.keys()))

    async def _on_table_item_clear(self, session: Session, packet: TablePacket) -> None:
        table = await self.get_table(packet.id)
        await table.clear()

    async def register_table[T: Keyable](self, table_type: TableType[T]) -> Table[T]:
        table = await self.get_table(table_type.identifier)
        return SerializedTable(table, table_type)

    async def get_table(self, identifier: Identifier) -> ServerTable:
        if identifier in self._tables:
            return self._tables[identifier]
        table = CachedTable(self._server, identifier)
        adapter = SqliteTableAdapter.create(self.get_table_path(identifier))
        await adapter.load()
        table.set_adapter(adapter)
        self._tables[identifier] = table
        return table

    def get_table_path(self, identifier: Identifier) -> Path:
        path = self._server.directories.get("tables") / identifier.get_sanitized_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def on_server_stop(self) -> None:
        for table in self._tables.values():
            await table.store()

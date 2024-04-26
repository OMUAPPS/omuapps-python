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
from omu.network.packet.packet_types import DisconnectType
from result import Err, Ok, Result

from omuserver.extension.table.serialized_table import SerializedTable
from omuserver.server import Server
from omuserver.session import Session

from .adapters.sqlitetable import SqliteTableAdapter
from .adapters.tableadapter import TableAdapter
from .cached_table import CachedTable
from .server_table import ServerTable


class TableExtension:
    def __init__(self, server: Server) -> None:
        self.server = server
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
            self.handle_bind_permission,
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_CONFIG_PACKET,
            self.handle_table_config,
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_LISTEN_PACKET,
            self.handler_listen,
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_PROXY_LISTEN_PACKET,
            self.handle_proxy_listen,
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_PROXY_PACKET,
            self.handle_proxy,
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_ADD_PACKET,
            self.handle_item_add,
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_UPDATE_PACKET,
            self.handle_item_update,
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_REMOVE_PACKET,
            self.handle_item_remove,
        )
        server.packet_dispatcher.add_packet_handler(
            TABLE_ITEM_CLEAR_PACKET,
            self.handle_item_clear,
        )
        server.endpoints.bind_endpoint(
            TABLE_ITEM_GET_ENDPOINT,
            self.handle_item_get,
        )
        server.endpoints.bind_endpoint(
            TABLE_FETCH_ENDPOINT,
            self.handle_item_fetch,
        )
        server.endpoints.bind_endpoint(
            TABLE_FETCH_ALL_ENDPOINT,
            self.handle_item_fetch_all,
        )
        server.endpoints.bind_endpoint(
            TABLE_SIZE_ENDPOINT,
            self.handle_table_size,
        )
        server.listeners.stop += self.on_server_stop

    async def handle_item_get(
        self, session: Session, packet: TableKeysPacket
    ) -> TableItemsPacket:
        table = await self.get_table(packet.id)
        items = await table.get_many(*packet.keys)
        return TableItemsPacket(
            id=packet.id,
            items=items,
        )

    async def handle_item_fetch(
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

    async def handle_item_fetch_all(
        self, session: Session, packet: TablePacket
    ) -> TableItemsPacket:
        table = await self.get_table(packet.id)
        items = await table.fetch_all()
        return TableItemsPacket(
            id=packet.id,
            items=items,
        )

    async def handle_table_size(self, session: Session, packet: TablePacket) -> int:
        table = await self.get_table(packet.id)
        return await table.size()

    async def handle_bind_permission(
        self, session: Session, packet: BindPermissionPacket
    ) -> None:
        table = await self.get_table(packet.id)
        if (await self.check_permission(session, table)).is_err():
            return
        table.bind_permission(packet.permission)

    async def handle_table_config(
        self, session: Session, packet: SetConfigPacket
    ) -> None:
        table = await self.get_table(packet.id)
        if (await self.check_permission(session, table)).is_err():
            return
        table.set_config(packet.config)

    async def handler_listen(self, session: Session, id: Identifier) -> None:
        table = await self.get_table(id)
        if (await self.check_permission(session, table)).is_err():
            return
        table.attach_session(session)

    async def handle_proxy_listen(self, session: Session, id: Identifier) -> None:
        table = await self.get_table(id)
        if (await self.check_permission(session, table)).is_err():
            return
        table.attach_proxy_session(session)

    async def handle_proxy(self, session: Session, packet: TableProxyPacket) -> None:
        table = await self.get_table(packet.id)
        if (await self.check_permission(session, table)).is_err():
            return
        await table.proxy(session, packet.key, packet.items)

    async def handle_item_add(self, session: Session, packet: TableItemsPacket) -> None:
        table = await self.get_table(packet.id)
        if (await self.check_permission(session, table)).is_err():
            return
        await table.add(packet.items)

    async def handle_item_update(
        self, session: Session, packet: TableItemsPacket
    ) -> None:
        table = await self.get_table(packet.id)
        if (await self.check_permission(session, table)).is_err():
            return
        await table.update(packet.items)

    async def handle_item_remove(
        self, session: Session, packet: TableItemsPacket
    ) -> None:
        table = await self.get_table(packet.id)
        if (await self.check_permission(session, table)).is_err():
            return
        await table.remove(list(packet.items.keys()))

    async def handle_item_clear(self, session: Session, packet: TablePacket) -> None:
        table = await self.get_table(packet.id)
        if (await self.check_permission(session, table)).is_err():
            return
        await table.clear()

    async def register_table[T: Keyable](self, table_type: TableType[T]) -> Table[T]:
        table = await self.get_table(table_type.identifier)
        return SerializedTable(table, table_type)

    async def get_table(self, id: Identifier) -> ServerTable:
        if id in self._tables:
            return self._tables[id]
        table = CachedTable(self.server, id)
        adapter = SqliteTableAdapter.create(self.get_table_path(id))
        await adapter.load()
        table.set_adapter(adapter)
        self._tables[id] = table
        return table

    def get_table_path(self, identifier: Identifier) -> Path:
        path = self.server.directories.get("tables") / identifier.get_sanitized_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def on_server_stop(self) -> None:
        for table in self._tables.values():
            await table.store()

    async def check_permission(self, session: Session, table: ServerTable) -> Result:
        if table.id.is_subpart_of(session.app.identifier):
            return Ok(None)
        if table.permission is None:
            await session.disconnect(
                DisconnectType.PERMISSION_DENIED,
                f"Table {table.id} does not have a permission set",
            )
            return Err(None)
        has_permission = self.server.permissions.has_permission(
            session, table.permission
        )
        if not has_permission:
            await session.disconnect(
                DisconnectType.PERMISSION_DENIED,
                f"Table {table.id} does not have permission {table.permission}",
            )
            return Err(None)
        return Ok(None)

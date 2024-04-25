from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

from omu.extension.table.table_extension import (
    TABLE_ITEM_ADD_PACKET,
    TABLE_ITEM_CLEAR_PACKET,
    TABLE_ITEM_REMOVE_PACKET,
    TABLE_ITEM_UPDATE_PACKET,
    TableItemsPacket,
    TablePacket,
)
from omu.identifier import Identifier

from omuserver.extension.table.server_table import ServerTable

if TYPE_CHECKING:
    from omuserver.session import Session


class SessionTableListener:
    def __init__(self, id: Identifier, session: Session, table: ServerTable) -> None:
        self.id = id
        self.session = session
        self.table = table
        table.listeners.add += self.on_add
        table.listeners.update += self.on_update
        table.listeners.remove += self.on_remove
        table.listeners.clear += self.on_clear

    def close(self) -> None:
        self.table.listeners.add -= self.on_add
        self.table.listeners.update -= self.on_update
        self.table.listeners.remove -= self.on_remove
        self.table.listeners.clear -= self.on_clear

    async def on_add(self, items: Mapping[str, Any]) -> None:
        if self.session.closed:
            return
        await self.session.send(
            TABLE_ITEM_ADD_PACKET,
            TableItemsPacket(
                id=self.id,
                items=items,
            ),
        )

    async def on_update(self, items: Mapping[str, Any]) -> None:
        if self.session.closed:
            return
        await self.session.send(
            TABLE_ITEM_UPDATE_PACKET,
            TableItemsPacket(
                id=self.id,
                items=items,
            ),
        )

    async def on_remove(self, items: Mapping[str, Any]) -> None:
        if self.session.closed:
            return
        await self.session.send(
            TABLE_ITEM_REMOVE_PACKET,
            TableItemsPacket(
                id=self.id,
                items=items,
            ),
        )

    async def on_clear(self) -> None:
        if self.session.closed:
            return
        await self.session.send(TABLE_ITEM_CLEAR_PACKET, TablePacket(id=self.id))

    def __repr__(self) -> str:
        return f"<SessionTableHandler key={self.id} app={self.session.app}>"

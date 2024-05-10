from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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
from omuserver.session import Session


class SessionTableListener:
    def __init__(self, id: Identifier, session: Session, table: ServerTable) -> None:
        self.id = id
        self.session = session
        self.table = table
        table.event.add += self.on_add
        table.event.update += self.on_update
        table.event.remove += self.on_remove
        table.event.clear += self.on_clear

    def close(self) -> None:
        self.table.event.add -= self.on_add
        self.table.event.update -= self.on_update
        self.table.event.remove -= self.on_remove
        self.table.event.clear -= self.on_clear

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

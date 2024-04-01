from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from omu.extension.table.table_extension import (
    TABLE_ITEM_ADD_PACKET,
    TABLE_ITEM_CLEAR_PACKET,
    TABLE_ITEM_REMOVE_EVENT,
    TABLE_ITEM_UPDATE_PACKET,
    TableEventData,
    TableItemsData,
)

from omuserver.extension.table.server_table import ServerTable

if TYPE_CHECKING:
    from omuserver.session import Session


class SessionTableListener:
    def __init__(self, id: str, session: Session, table: ServerTable) -> None:
        self._id = id
        self._session = session
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

    async def on_add(self, items: Dict[str, Any]) -> None:
        if self._session.closed:
            return
        await self._session.send(
            TABLE_ITEM_ADD_PACKET,
            TableItemsData(
                items=items,
                type=self._id,
            ),
        )

    async def on_update(self, items: Dict[str, Any]) -> None:
        if self._session.closed:
            return
        await self._session.send(
            TABLE_ITEM_UPDATE_PACKET,
            TableItemsData(
                items=items,
                type=self._id,
            ),
        )

    async def on_remove(self, items: Dict[str, Any]) -> None:
        if self._session.closed:
            return
        await self._session.send(
            TABLE_ITEM_REMOVE_EVENT,
            TableItemsData(
                items=items,
                type=self._id,
            ),
        )

    async def on_clear(self) -> None:
        if self._session.closed:
            return
        await self._session.send(TABLE_ITEM_CLEAR_PACKET, TableEventData(type=self._id))

    def __repr__(self) -> str:
        return f"<SessionTableHandler key={self._id} app={self._session.app}>"

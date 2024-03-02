from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from omu.extension.table.table_extension import (
    TableEventData,
    TableItemAddEvent,
    TableItemClearEvent,
    TableItemRemoveEvent,
    TableItemsData,
    TableItemUpdateEvent,
)

from .server_table import ServerTableListener

if TYPE_CHECKING:
    from omuserver.session import Session


class SessionTableListener(ServerTableListener):
    def __init__(self, id: str, session: Session) -> None:
        self._id = id
        self._session = session

    async def on_add(self, items: Dict[str, Any]) -> None:
        if self._session.closed:
            return
        await self._session.send(
            TableItemAddEvent,
            TableItemsData(
                items=items,
                type=self._id,
            ),
        )

    async def on_update(self, items: Dict[str, Any]) -> None:
        if self._session.closed:
            return
        await self._session.send(
            TableItemUpdateEvent,
            TableItemsData(
                items=items,
                type=self._id,
            ),
        )

    async def on_remove(self, items: Dict[str, Any]) -> None:
        if self._session.closed:
            return
        await self._session.send(
            TableItemRemoveEvent,
            TableItemsData(
                items=items,
                type=self._id,
            ),
        )

    async def on_clear(self) -> None:
        if self._session.closed:
            return
        await self._session.send(TableItemClearEvent, TableEventData(type=self._id))

    def __repr__(self) -> str:
        return f"<SessionTableHandler key={self._id} app={self._session.app}>"

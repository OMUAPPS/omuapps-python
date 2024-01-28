from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from omu.extension.table.table_extension import (
    TableEventData,
    TableItemAddEvent,
    TableItemClearEvent,
    TableItemRemoveEvent,
    TableItemsEventData,
    TableItemUpdateEvent,
)

from .server_table import TableListener

if TYPE_CHECKING:
    from omu.extension.table.model import TableInfo
    from omu.interface import Serializable

    from omuserver.session import Session


class SessionTableListener(TableListener):
    def __init__(
        self, info: TableInfo, session: Session, serializer: Serializable
    ) -> None:
        self._info = info
        self._session = session
        self._serializer = serializer

    async def on_add(self, items: Dict[str, Any]) -> None:
        if self._session.closed:
            return
        await self._session.send(
            TableItemAddEvent,
            TableItemsEventData(
                items={
                    key: self._serializer.serialize(value)
                    for key, value in items.items()
                },
                type=self._info.key(),
            ),
        )

    async def on_update(self, items: Dict[str, Any]) -> None:
        if self._session.closed:
            return
        await self._session.send(
            TableItemUpdateEvent,
            TableItemsEventData(
                items={
                    key: self._serializer.serialize(value)
                    for key, value in items.items()
                },
                type=self._info.key(),
            ),
        )

    async def on_remove(self, items: Dict[str, Any]) -> None:
        if self._session.closed:
            return
        await self._session.send(
            TableItemRemoveEvent,
            TableItemsEventData(
                items={
                    key: self._serializer.serialize(value)
                    for key, value in items.items()
                },
                type=self._info.key(),
            ),
        )

    async def on_clear(self) -> None:
        if self._session.closed:
            return
        await self._session.send(
            TableItemClearEvent, TableEventData(type=self._info.key())
        )

    def __repr__(self) -> str:
        return (
            f"<SessionTableHandler info={self._info.key()} session={self._session.app}>"
        )

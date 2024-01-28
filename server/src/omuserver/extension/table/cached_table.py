from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, AsyncIterator, Dict, List

from omu.extension.table.model import TableInfo
from omu.extension.table.table_extension import TableProxyEvent, TableProxyEventData

from omuserver.session import SessionListener

from .adapters.tableadapter import Json, TableAdapter
from .server_table import ServerTable, TableListener
from .session_table_handler import SessionTableListener

if TYPE_CHECKING:
    from omu.interface import Serializable

    from omuserver.server import Server
    from omuserver.session import Session


class CachedTable[T](ServerTable[T], SessionListener):
    def __init__(
        self,
        server: Server,
        info: TableInfo,
        serializer: Serializable[T, Json],
        table: TableAdapter,
    ):
        self._server = server
        self._info = info
        self._serializer = serializer
        self._table = table
        self._cache: Dict[str, T] = {}
        self._use_cache = info.cache or False
        self._cache: Dict[str, T] = {}
        self._cache_size = info.cache_size or 512
        self._listeners: list[TableListener[T]] = []
        self._sessions: Dict[Session, SessionTableListener] = {}
        self._proxy_sessions: List[Session] = []
        self._changed = False
        self._loaded = False
        self._key = 0
        self._save_task: asyncio.Task | None = None

    async def store(self) -> None:
        if not self._loaded:
            raise Exception("Table not loaded")
        if not self._changed:
            return
        self._changed = False
        await self._table.store()

    async def load(self) -> None:
        if self._changed:
            raise Exception("Table not stored")
        if self._loaded:
            return
        await self._table.load()
        self._loaded = True

    @property
    def cache(self) -> Dict[str, T]:
        return self._cache

    @property
    def serializer(self) -> Serializable[T, Json]:
        return self._serializer

    def attach_session(self, session: Session) -> None:
        if session in self._sessions:
            return
        handler = SessionTableListener(self._info, session, self._serializer)
        self._sessions[session] = handler
        self.add_listener(handler)
        session.add_listener(self)

    def detach_session(self, session: Session) -> None:
        if session in self._proxy_sessions:
            self._proxy_sessions.remove(session)
        if session in self._sessions:
            handler = self._sessions.pop(session)
            self.remove_listener(handler)

    async def on_disconnected(self, session: Session) -> None:
        self.detach_session(session)

    def attach_proxy_session(self, session: Session) -> None:
        self._proxy_sessions.append(session)

    async def get(self, key: str) -> T | None:
        if key in self._cache:
            return self._cache[key]
        data = await self._table.get(key)
        if data is None:
            return None
        item = self._serializer.deserialize(data)
        await self.update_cache({key: item})
        return item

    async def get_all(self, keys: List[str]) -> Dict[str, T]:
        items = {}
        for key in tuple(keys):
            if key in self._cache:
                items[key] = self._cache[key]
                keys.remove(key)
        if len(keys) == 0:
            return items
        data = await self._table.get_all(keys)
        for key, value in data.items():
            item = self._serializer.deserialize(value)
            items[key] = item
        await self.update_cache(items)
        return items

    async def add(self, items: Dict[str, T]) -> None:
        if len(self._proxy_sessions) > 0:
            await self.send_proxy_event(items)
            return
        await self._table.set_all(
            {key: self._serializer.serialize(value) for key, value in items.items()}
        )
        for listener in self._listeners:
            await listener.on_add(items)
        await self.update_cache(items)
        self.mark_changed()

    async def send_proxy_event(self, items: Dict[str, T]) -> None:
        session = self._proxy_sessions[0]
        self._key += 1
        await session.send(
            TableProxyEvent,
            TableProxyEventData(
                items={
                    key: self._serializer.serialize(value)
                    for key, value in items.items()
                },
                type=self._info.key(),
                key=self._key,
            ),
        )

    async def proxy(self, session: Session, key: int, items: Dict[str, T]) -> int:
        if key != self._key:
            return 0
        if session not in self._proxy_sessions:
            raise ValueError("Session not in proxy sessions")
        index = self._proxy_sessions.index(session)
        if index == len(self._proxy_sessions) - 1:
            await self._table.set_all(
                {key: self._serializer.serialize(value) for key, value in items.items()}
            )
            for listener in self._listeners:
                await listener.on_add(items)
            await self.update_cache(items)
            self.mark_changed()
            return 0
        session = self._proxy_sessions[index + 1]
        await session.send(
            TableProxyEvent,
            TableProxyEventData(
                items=items,
                type=self._info.key(),
                key=self._key,
            ),
        )
        return self._key

    async def update(self, items: Dict[str, T]) -> None:
        await self._table.set_all(
            {key: self._serializer.serialize(value) for key, value in items.items()}
        )
        for listener in self._listeners:
            await listener.on_update(items)
        await self.update_cache(items)
        self.mark_changed()

    async def remove(self, items: list[str]) -> None:
        data = await self._table.get_all(items)
        removed = {
            key: self._serializer.deserialize(value) for key, value in data.items()
        }
        await self._table.remove_all(items)
        for key in items:
            if key in self._cache:
                del self._cache[key]
        for listener in self._listeners:
            await listener.on_remove(removed)
        self.mark_changed()

    async def clear(self) -> None:
        await self._table.clear()
        for listener in self._listeners:
            await listener.on_clear()
        self._cache.clear()
        self.mark_changed()

    async def fetch(
        self,
        before: int | None = None,
        after: str | None = None,
        cursor: str | None = None,
    ) -> Dict[str, T]:
        items = await self._table.fetch(before, after, cursor)
        return {
            key: self._serializer.deserialize(value) for key, value in items.items()
        }

    async def iterator(self) -> AsyncIterator[T]:
        cursor: str | None = None
        while True:
            items = await self.fetch(self._cache_size, cursor)
            if len(items) == 0:
                break
            for item in items.values():
                yield item
            *_, cursor = items.keys()

    async def size(self) -> int:
        return len(self._cache)

    def add_listener(self, listener: TableListener[T]) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: TableListener[T]) -> None:
        self._listeners.remove(listener)

    async def save_task(self) -> None:
        while self._changed:
            await self.store()
            await asyncio.sleep(30)

    def mark_changed(self) -> None:
        self._changed = True
        if self._save_task is None:
            self._save_task = asyncio.create_task(self.save_task())

    async def update_cache(self, items: Dict[str, T]) -> None:
        if not self.cache:
            return
        for key, item in items.items():
            self._cache[key] = item
            if len(self._cache) > self._cache_size:
                del self._cache[next(iter(self._cache))]
        for listener in self._listeners:
            await listener.on_cache_update(self._cache)

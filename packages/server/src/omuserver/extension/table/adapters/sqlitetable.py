from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict

from .tableadapter import Json, TableAdapter, json


class SqliteTableAdapter(TableAdapter):
    def __init__(self, path: Path) -> None:
        self._path = path
        self._conn = sqlite3.connect(str(path / "data.db"))
        self._conn.execute(
            # index, key, value
            "CREATE TABLE IF NOT EXISTS data ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "key TEXT UNIQUE,"
            "value TEXT"
            ")"
        )
        self._conn.commit()

    @classmethod
    def create(cls, path: Path) -> TableAdapter:
        return cls(path)

    async def store(self) -> None:
        self._conn.commit()

    async def load(self) -> None:
        pass

    async def get(self, key: str) -> Json | None:
        cursor = self._conn.execute("SELECT value FROM data WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    async def get_all(self, keys: list[str]) -> Dict[str, Json]:
        cursor = self._conn.execute(
            f"SELECT key, value FROM data WHERE key IN ({','.join('?' for _ in keys)})",
            keys,
        )
        rows = cursor.fetchall()
        return {row[0]: json.loads(row[1]) for row in rows}

    async def set(self, key: str, value: Json) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO data (key, value) VALUES (?, ?)",
            (key, json.dumps(value)),
        )

    async def set_all(self, items: Dict[str, Json]) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO data (key, value) VALUES (?, ?)",
            ((key, json.dumps(value)) for key, value in items.items()),
        )

    async def remove(self, key: str) -> None:
        self._conn.execute("DELETE FROM data WHERE key = ?", (key,))

    async def remove_all(self, keys: list[str]) -> None:
        self._conn.execute(
            f"DELETE FROM data WHERE key IN ({','.join('?' for _ in keys)})",
            keys,
        )

    async def fetch(
        self, before: int | None, after: int | None, cursor: str | None
    ) -> Dict[str, Json]:
        if cursor is not None:
            _cursor = self._conn.execute("SELECT id FROM data WHERE key = ?", (cursor,))
            row = _cursor.fetchone()
            if row is None:
                raise ValueError(f"Cursor {cursor} not found")
            cursor = row[0]

        items = {}
        if before is not None:
            if cursor is None:
                _cursor = self._conn.execute(
                    "SELECT id, key, value FROM data ORDER BY id DESC LIMIT ?",
                    (before,),
                )
            else:
                _cursor = self._conn.execute(
                    "SELECT id, key, value FROM data WHERE id <= ? ORDER BY id DESC LIMIT ?",
                    (cursor, before),
                )
            items.update(
                {row[0]: (row[1], json.loads(row[2])) for row in _cursor.fetchall()}
            )
        if after is not None:
            if cursor is None:
                _cursor = self._conn.execute(
                    "SELECT id, key, value FROM data ORDER BY id LIMIT ?",
                    (after,),
                )
            else:
                _cursor = self._conn.execute(
                    "SELECT id, key, value FROM data WHERE id >= ? ORDER BY id LIMIT ?",
                    (cursor, after),
                )
            items.update(
                {row[0]: (row[1], json.loads(row[2])) for row in _cursor.fetchall()}
            )
        return {key: value for _, (key, value) in sorted(items.items(), reverse=True)}

    async def first(self) -> str | None:
        _cursor = self._conn.execute("SELECT key FROM data ORDER BY id LIMIT 1")
        row = _cursor.fetchone()
        if row is None:
            return None
        return row[0]

    async def last(self) -> str | None:
        _cursor = self._conn.execute("SELECT key FROM data ORDER BY id DESC LIMIT 1")
        row = _cursor.fetchone()
        if row is None:
            return None
        return row[0]

    async def clear(self) -> None:
        self._conn.execute("DELETE FROM data")

    async def size(self) -> int:
        _cursor = self._conn.execute("SELECT COUNT(*) FROM data")
        row = _cursor.fetchone()
        if row is None:
            return 0
        return row[0]

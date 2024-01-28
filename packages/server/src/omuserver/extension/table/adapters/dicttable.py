from pathlib import Path
from typing import Dict, List

from .tableadapter import Json, TableAdapter, json


class DictTableAdapter(TableAdapter):
    def __init__(self, path: Path) -> None:
        self._path = path / "data.json"
        self._data: Dict[str, Json] = {}

    @classmethod
    def create(cls, path: Path) -> TableAdapter:
        return cls(path)

    async def store(self) -> None:
        self._path.write_text(json.dumps(self._data), encoding="utf-8")

    async def load(self) -> None:
        if not self._path.exists():
            self._data = {}
            return
        data = self._path.read_text(encoding="utf-8")
        items = json.loads(data)
        if not isinstance(items, dict):
            raise ValueError("Invalid data")
        self._data = {key: value for key, value in items.items()}

    async def get(self, key: str) -> Json | None:
        return self._data.get(key, None)

    async def get_all(self, keys: List[str]) -> Dict[str, Json]:
        return {key: self._data[key] for key in keys if key in self._data}

    async def set(self, key: str, value: Json) -> None:
        self._data[key] = value

    async def set_all(self, items: Dict[str, Json]) -> None:
        self._data.update(items)

    async def remove(self, key: str) -> None:
        del self._data[key]

    async def remove_all(self, keys: List[str]) -> None:
        for key in keys:
            if key in self._data:
                del self._data[key]

    async def fetch(
        self, before: int | None, after: int | None, cursor: str | None
    ) -> Dict[str, Json]:
        keys = list(self._data.keys())
        if cursor is None:
            cursor = await self.first() if before is not None else await self.last()
        if cursor is None:
            return {}
        if cursor not in keys:
            raise ValueError("Invalid cursor")
        index = keys.index(cursor)
        if before is not None:
            keys = keys[max(0, index - before) :]
        if after is not None:
            keys = keys[: min(len(keys), index + after + 1)]
        return {key: self._data[key] for key in keys}

    async def first(self) -> str | None:
        if not self._data:
            return None
        return tuple(self._data.keys())[0]

    async def last(self) -> str | None:
        if not self._data:
            return None
        return tuple(self._data.keys())[-1]

    async def clear(self) -> None:
        self._data.clear()

    async def size(self) -> int:
        return len(self._data)

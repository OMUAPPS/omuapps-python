from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping, Sequence

from omu.identifier import Identifier
from omu.network.bytebuffer import ByteReader, ByteWriter

from .table import TableConfig


@dataclass
class TablePacket:
    id: Identifier

    @classmethod
    def serialize(cls, item: TablePacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.id.key())
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> TablePacket:
        with ByteReader(item) as reader:
            id = reader.read_string()
        return TablePacket(id=Identifier.from_key(id))


@dataclass
class TableItemsPacket:
    id: Identifier
    items: Mapping[str, bytes]

    @classmethod
    def serialize(cls, item: TableItemsPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.id.key())
        writer.write_int(len(item.items))
        for key, value in item.items.items():
            writer.write_string(key)
            writer.write_byte_array(value)
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> TableItemsPacket:
        with ByteReader(item) as reader:
            id = reader.read_string()
            item_count = reader.read_int()
            items: Mapping[str, bytes] = {}
            for _ in range(item_count):
                item_key = reader.read_string()
                value = reader.read_byte_array()
                items[item_key] = value
        return TableItemsPacket(id=Identifier.from_key(id), items=items)


@dataclass
class TableKeysPacket:
    id: Identifier
    keys: Sequence[str]

    @classmethod
    def serialize(cls, item: TableKeysPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.id.key())
        writer.write_int(len(item.keys))
        for key in item.keys:
            writer.write_string(key)
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> TableKeysPacket:
        with ByteReader(item) as reader:
            id = reader.read_string()
            key_count = reader.read_int()
            keys = [reader.read_string() for _ in range(key_count)]
        return TableKeysPacket(id=Identifier.from_key(id), keys=keys)


@dataclass
class TableProxyPacket:
    id: Identifier
    items: Mapping[str, bytes]
    key: int

    @classmethod
    def serialize(cls, item: TableProxyPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.id.key())
        writer.write_int(item.key)
        writer.write_int(len(item.items))
        for key, value in item.items.items():
            writer.write_string(key)
            writer.write_byte_array(value)
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> TableProxyPacket:
        with ByteReader(item) as reader:
            id = reader.read_string()
            key = reader.read_int()
            item_count = reader.read_int()
            items: Mapping[str, bytes] = {}
            for _ in range(item_count):
                item_key = reader.read_string()
                value = reader.read_byte_array()
                items[item_key] = value
        return TableProxyPacket(
            id=Identifier.from_key(id),
            key=key,
            items=items,
        )


@dataclass
class TableFetchPacket:
    id: Identifier
    before: int | None
    after: int | None
    cursor: str | None

    @classmethod
    def serialize(cls, item: TableFetchPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.id.key())
        flags = 0
        if item.before is not None:
            flags |= 0b1
        if item.after is not None:
            flags |= 0b10
        if item.cursor is not None:
            flags |= 0b100
        writer.write_byte(flags)
        if item.before is not None:
            writer.write_int(item.before)
        if item.after is not None:
            writer.write_int(item.after)
        if item.cursor is not None:
            writer.write_string(item.cursor)
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> TableFetchPacket:
        with ByteReader(item) as reader:
            id = reader.read_string()
            flags = reader.read_byte()
            before = reader.read_int() if flags & 0b1 else None
            after = reader.read_int() if flags & 0b10 else None
            cursor = reader.read_string() if flags & 0b100 else None
        return TableFetchPacket(
            id=Identifier.from_key(id),
            before=before,
            after=after,
            cursor=cursor,
        )


@dataclass
class SetConfigPacket:
    id: Identifier
    config: TableConfig

    @classmethod
    def serialize(cls, item: SetConfigPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.id.key())
        writer.write_string(json.dumps(item.config))
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> SetConfigPacket:
        with ByteReader(item) as reader:
            id = reader.read_string()
            config = json.loads(reader.read_string())
        return SetConfigPacket(id=Identifier.from_key(id), config=config)


@dataclass
class BindPermissionPacket:
    id: Identifier
    permission: Identifier

    @staticmethod
    def serialize(item: BindPermissionPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.id.key())
        writer.write_string(item.permission.key())
        return writer.finish()

    @staticmethod
    def deserialize(item: bytes) -> BindPermissionPacket:
        with ByteReader(item) as reader:
            id = reader.read_string()
            permission = reader.read_string()
        return BindPermissionPacket(
            id=Identifier.from_key(id),
            permission=Identifier.from_key(permission),
        )

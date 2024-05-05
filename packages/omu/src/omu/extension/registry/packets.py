from __future__ import annotations

from dataclasses import dataclass

from omu.helper import map_optional
from omu.identifier import Identifier
from omu.network.bytebuffer import ByteReader, ByteWriter, Flags


@dataclass(frozen=True)
class RegistryPacket:
    id: Identifier
    value: bytes | None

    @classmethod
    def serialize(cls, item: RegistryPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.id.key())
        writer.write_boolean(item.value is not None)
        if item.value is not None:
            writer.write_byte_array(item.value)
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> RegistryPacket:
        with ByteReader(item) as reader:
            key = Identifier.from_key(reader.read_string())
            existing = reader.read_boolean()
            value = reader.read_byte_array() if existing else None
        return RegistryPacket(key, value)


@dataclass(frozen=True)
class RegistryPermissions:
    all: Identifier | None = None
    read: Identifier | None = None
    write: Identifier | None = None

    def serialize(self, writer: ByteWriter) -> None:
        flags = Flags(0, 3)
        flags = flags.set(0, self.all is not None)
        flags = flags.set(1, self.read is not None)
        flags = flags.set(2, self.write is not None)
        writer.write_flags(flags)
        if self.all is not None:
            writer.write_string(self.all.key())
        if self.read is not None:
            writer.write_string(self.read.key())
        if self.write is not None:
            writer.write_string(self.write.key())

    @classmethod
    def deserialize(cls, reader: ByteReader) -> RegistryPermissions:
        flags = reader.read_flags(3)
        all_id = reader.read_string() if flags.has(0) else None
        read_id = reader.read_string() if flags.has(1) else None
        write_id = reader.read_string() if flags.has(2) else None
        return RegistryPermissions(
            map_optional(all_id, Identifier.from_key),
            map_optional(read_id, Identifier.from_key),
            map_optional(write_id, Identifier.from_key),
        )


@dataclass(frozen=True)
class RegistryRegisterPacket:
    id: Identifier
    permissions: RegistryPermissions

    @classmethod
    def serialize(cls, item: RegistryRegisterPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.id.key())
        item.permissions.serialize(writer)
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> RegistryRegisterPacket:
        with ByteReader(item) as reader:
            key = Identifier.from_key(reader.read_string())
            permissions = RegistryPermissions.deserialize(reader)
        return RegistryRegisterPacket(key, permissions)

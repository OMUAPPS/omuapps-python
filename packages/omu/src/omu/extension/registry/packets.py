from __future__ import annotations

from dataclasses import dataclass

from omu.identifier import Identifier
from omu.network.bytebuffer import ByteReader, ByteWriter


@dataclass(frozen=True)
class RegistryPacket:
    identifier: Identifier
    value: bytes | None

    @classmethod
    def serialize(cls, item: RegistryPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.identifier.key())
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

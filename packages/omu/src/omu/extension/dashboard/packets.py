from __future__ import annotations

import json
from dataclasses import dataclass
from typing import List

from omu.app import App
from omu.bytebuffer import ByteReader, ByteWriter
from omu.extension.permission.permission import PermissionType
from omu.extension.plugin.package_info import PackageInfo


@dataclass(frozen=True)
class PermissionRequestPacket:
    request_id: str
    app: App
    permissions: List[PermissionType]

    @classmethod
    def serialize(cls, item: PermissionRequestPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.request_id)
        writer.write_string(json.dumps(item.app.to_json()))
        writer.write_string(json.dumps(map(PermissionType.to_json, item.permissions)))
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> PermissionRequestPacket:
        with ByteReader(item) as reader:
            request_id = reader.read_string()
            app = App.from_json(json.loads(reader.read_string()))
            permissions = map(
                PermissionType.from_json, json.loads(reader.read_string())
            )
            return cls(request_id, app, list(permissions))


@dataclass(frozen=True)
class PluginRequestPacket:
    request_id: str
    app: App
    packages: list[PackageInfo]

    @classmethod
    def serialize(cls, item: PluginRequestPacket) -> bytes:
        writer = ByteWriter()
        writer.write_string(item.request_id)
        writer.write_string(json.dumps(item.app.to_json()))
        writer.write_string(json.dumps(item.packages))
        return writer.finish()

    @classmethod
    def deserialize(cls, item: bytes) -> PluginRequestPacket:
        with ByteReader(item) as reader:
            request_id = reader.read_string()
            app = App.from_json(json.loads(reader.read_string()))
            plugins = map(PackageInfo, json.loads(reader.read_string()))
            return cls(request_id, app, list(plugins))

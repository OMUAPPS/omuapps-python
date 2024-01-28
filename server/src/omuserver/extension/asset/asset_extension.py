from __future__ import annotations

import base64
from typing import TYPE_CHECKING, Dict, List

from omu.extension.asset.asset_extension import AssetUploadEndpoint

from omuserver.extension import Extension
from omuserver.utils.helper import safe_path_join

if TYPE_CHECKING:
    from omuserver.server import Server
    from omuserver.session import Session


class AssetExtension(Extension):
    def __init__(self, server: Server) -> None:
        self._server = server
        server.endpoints.bind_endpoint(AssetUploadEndpoint, self._on_upload)

    async def _on_upload(self, session: Session, files: Dict[str, str]) -> List[str]:
        for key, data in files.items():
            path = safe_path_join(self._server.directories.assets, key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self._decode(data))
        return list(files.keys())

    def _decode(self, data: str) -> bytes:
        return base64.b64decode(data.encode("utf-8"))

    @classmethod
    def create(cls, server: Server) -> AssetExtension:
        return cls(server)

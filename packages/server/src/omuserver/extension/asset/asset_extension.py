from __future__ import annotations

from typing import TYPE_CHECKING, List

from omu.extension.asset.asset_extension import (
    ASSET_DOWNLOAD_ENDPOINT,
    ASSET_UPLOAD_ENDPOINT,
    Files,
)
from omu.identifier import Identifier

from omuserver.helper import safe_path_join

if TYPE_CHECKING:
    from omuserver.server import Server
    from omuserver.session import Session


class AssetExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        server.endpoints.bind_endpoint(ASSET_UPLOAD_ENDPOINT, self.handle_upload)
        server.endpoints.bind_endpoint(ASSET_DOWNLOAD_ENDPOINT, self.handle_download)

    async def handle_upload(self, session: Session, files: Files) -> List[Identifier]:
        uploaded_files = []
        for file_identifier, file_data in files.items():
            path = file_identifier.to_path()
            file_path = safe_path_join(self._server.directories.assets, path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(file_data)
            uploaded_files.append(file_identifier)
        return uploaded_files

    async def handle_download(
        self, session: Session, identifiers: List[Identifier]
    ) -> Files:
        files = {}
        for identifier in identifiers:
            path = identifier.to_path()
            file_path = safe_path_join(self._server.directories.assets, path)
            if file_path.exists():
                files[identifier] = file_path.read_bytes()
        return files

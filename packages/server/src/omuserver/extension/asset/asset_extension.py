from __future__ import annotations

from typing import TYPE_CHECKING, List

from omu.extension.asset.asset_extension import AssetUploadEndpoint, Files

from omuserver.helper import safe_path_join

if TYPE_CHECKING:
    from omuserver.server import Server
    from omuserver.session import Session


class AssetExtension:
    def __init__(self, server: Server) -> None:
        self._server = server
        server.endpoints.bind_endpoint(AssetUploadEndpoint, self.handle_upload)

    async def handle_upload(self, session: Session, files: Files) -> List[str]:
        uploaded_files = []
        for file_name, file_data in files.items():
            file_path = safe_path_join(self._server.directories.assets, file_name)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(file_data)
            uploaded_files.append(file_name)
        return uploaded_files

import abc
import random
import string
from typing import Dict, Tuple

import sqlitedict
from loguru import logger
from omuserver import Server
from omuserver.security import Permission
from omuserver.security.permission import AdminPermissions, Permissions

from omu import App

type Token = str


class Security(abc.ABC):
    @abc.abstractmethod
    async def get_token(self, app: App, token: Token | None = None) -> Token | None:
        ...

    @abc.abstractmethod
    async def auth_app(
        self, app: App, token: Token | None = None
    ) -> Tuple[Permission, Token]:
        ...

    @abc.abstractmethod
    async def add_permissions(self, token: Token, permissions: Permission) -> None:
        ...

    @abc.abstractmethod
    async def get_permissions(self, token: Token) -> Permission:
        ...


class ServerSecurity(Security):
    def __init__(self, server: Server) -> None:
        self._server = server
        self._permissions: Dict[Token, Permission] = sqlitedict.SqliteDict(
            server.directories.get("security") / "tokens.sqlite", autocommit=True
        )

    async def get_token(self, app: App, token: Token | None = None) -> Token | None:
        if token is None:
            token = self._generate_token()
            self._permissions[token] = Permissions(app.key())
        elif token not in self._permissions:
            return None
        return token

    async def _get_token(self, app: App, token: Token | None = None) -> Token:
        if token is None:
            token = await self.get_token(app)
            if token is None:
                logger.warning(f"Failed to generate token for {app}")
                raise ValueError("Failed to generate token")
        elif token not in self._permissions:
            logger.warning(f"Invalid token {token} for {app}")
            token = await self.get_token(app)
            if token is None:
                logger.warning(f"Failed to generate token for {app}")
                raise ValueError("Failed to generate token")
        return token

    async def auth_app(
        self, app: App, token: Token | None = None
    ) -> Tuple[Permission, Token]:
        token = await self._get_token(app, token)
        permissions = await self.get_permissions(token)
        if permissions.owner != app.key() and not isinstance(
            permissions, AdminPermissions
        ):
            permissions = Permissions(app.key())
        return permissions, token

    async def add_permissions(self, token: Token, permissions: Permission) -> None:
        self._permissions[token] = permissions

    async def get_permissions(self, token: Token) -> Permission:
        return self._permissions[token]

    def _generate_token(self):
        return "".join(random.choices(string.ascii_letters + string.digits, k=16))

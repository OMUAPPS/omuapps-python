import abc
import datetime
import random
import sqlite3
import string

from loguru import logger
from omu import App

from omuserver.server import Server

type Token = str


class Security(abc.ABC):
    @abc.abstractmethod
    async def generate_app_token(self, app: App) -> Token: ...

    @abc.abstractmethod
    async def validate_app_token(self, app: App, token: Token) -> bool: ...

    @abc.abstractmethod
    async def verify_app_token(self, app: App, token: Token | None) -> Token: ...

    @abc.abstractmethod
    async def generate_plugin_token(self) -> Token: ...

    @abc.abstractmethod
    async def is_plugin_token(self, token: Token) -> bool: ...

    @abc.abstractmethod
    async def is_dashboard_token(self, token: Token) -> bool: ...


class TokenGenerator:
    def __init__(self):
        self._chars = string.ascii_letters + string.digits

    def generate(self, length: int) -> str:
        return "".join(random.choices(self._chars, k=length))


class ServerAuthenticator(Security):
    def __init__(self, server: Server):
        self._server = server
        self._plugin_tokens: set[str] = set()
        self._token_generator = TokenGenerator()
        self._token_db = sqlite3.connect(
            server.directories.get("security") / "tokens.sqlite"
        )
        self._token_db.execute(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                identifier TEXT,
                created_at INTEGER,
                last_used_at INTEGER
            )
            """
        )

    async def generate_app_token(self, app: App) -> Token:
        token = self._token_generator.generate(32)
        self._token_db.execute(
            """
            INSERT INTO tokens (token, identifier, created_at, last_used_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                token,
                app.id.key(),
                datetime.datetime.now(),
                datetime.datetime.now(),
            ),
        )
        self._token_db.commit()
        return token

    async def validate_app_token(self, app: App, token: Token) -> bool:
        if self._server.config.dashboard_token == token:
            return True
        cursor = self._token_db.execute(
            """
            SELECT token
            FROM tokens
            WHERE token = ? AND identifier = ?
            """,
            (token, app.id.key()),
        )
        result = cursor.fetchone()
        if result is None:
            return False
        self._token_db.execute(
            """
            UPDATE tokens
            SET last_used_at = ?
            WHERE token = ?
            """,
            (datetime.datetime.now(), token),
        )
        return True

    async def verify_app_token(self, app: App, token: str | None) -> str:
        if token is None:
            token = await self.generate_app_token(app)
        verified = await self.validate_app_token(app, token)
        if not verified:
            logger.warning(f"Invalid token: {token}")
            logger.info(f"Generating new token for {app}")
            token = await self.generate_app_token(app)
        return token

    async def is_dashboard_token(self, token: Token) -> bool:
        dashboard_token = self._server.config.dashboard_token
        if dashboard_token is None:
            return False
        return dashboard_token == token

    async def generate_plugin_token(self) -> Token:
        token = self._token_generator.generate(32)
        self._plugin_tokens.add(token)
        return token

    async def is_plugin_token(self, token: Token) -> bool:
        return token in self._plugin_tokens

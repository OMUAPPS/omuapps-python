import abc
import datetime
import random
import sqlite3

from omu import App

from omuserver.server import Server

type Token = str


class Security(abc.ABC):
    @abc.abstractmethod
    async def generate_app_token(self, app: App) -> Token: ...

    @abc.abstractmethod
    async def validate_app_token(self, app: App, token: Token) -> bool: ...


class TokenGenerator:
    def __init__(self):
        self._chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    def generate(self, length: int) -> str:
        return "".join(random.choices(self._chars, k=length))


class ServerAuthenticator(Security):
    def __init__(self, server: Server):
        self._server = server
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
                app.identifier.key(),
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
            (token, app.identifier.key()),
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

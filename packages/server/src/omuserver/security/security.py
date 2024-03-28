import abc
import datetime
import sqlite3

from omu import App

from omuserver.server import Server

type Token = str


class Security(abc.ABC):
    @abc.abstractmethod
    async def generate_app_token(self, app: App) -> Token: ...

    @abc.abstractmethod
    async def validate_app_token(self, app: App, token: Token) -> bool: ...


class ServerAuthenticator(Security):
    def __init__(self, server: Server):
        self._server = server
        self._token_db = sqlite3.connect(
            server.directories.get("security") / "tokens.sqlite"
        )
        self._token_db.execute(
            """
            CREATE TABLE IF NOT EXISTS tokens (
                identifier TEXT,
                token TEXT,
                created_at INTEGER,
                last_used_at INTEGER
            )
            """
        )

    async def generate_app_token(self, app: App) -> Token:
        token = app.identifier.key()
        self._token_db.execute(
            """
            INSERT INTO tokens (identifier, token, created_at, last_used_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                app.identifier.key(),
                token,
                datetime.datetime.now().timestamp(),
                datetime.datetime.now().timestamp(),
            ),
        )
        self._token_db.commit()
        return token

    async def validate_app_token(self, app: App, token: Token) -> bool:
        cursor = self._token_db.execute(
            """
            SELECT created_at, last_used_at FROM tokens
            WHERE identifier = ? AND token = ?
            """,
            (app.identifier.key(), token),
        )
        result = cursor.fetchone()
        if result is None:
            return False
        return True

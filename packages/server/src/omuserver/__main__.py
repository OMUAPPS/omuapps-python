import asyncio
import io
import sys
import tracemalloc
from pathlib import Path

import click
from loguru import logger
from omu import Address

from omuserver.directories import get_directories
from omuserver.security.permission import AdminPermissions
from omuserver.server.omuserver import OmuServer


def setup_logging():
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")
    logger.add(
        "logs/{time:YYYY-MM-DD}.log",
        rotation="1 day",
        colorize=False,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )


@click.command()
@click.option("--debug", is_flag=True)
@click.option("--token", type=str, default=None)
def main(debug: bool, token: str | None):
    loop = asyncio.get_event_loop()
    directories = get_directories()
    address = Address(
        host="0.0.0.0",
        port=26423,
        secure=False,
    )

    if debug:
        logger.warning("Debug mode enabled")
        directories.plugins = (Path.cwd() / ".." / "plugins").resolve()
        tracemalloc.start()

    server = OmuServer(address, directories=directories, loop=loop)
    if token:
        loop.run_until_complete(
            server.security.add_permissions(token, AdminPermissions("admin"))
        )

    logger.info("Starting server...")
    server.run()


if __name__ == "__main__":
    setup_logging()
    main()

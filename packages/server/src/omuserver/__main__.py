import asyncio
import io
import sys
import tracemalloc
from pathlib import Path
from typing import Callable, Coroutine

import click
from loguru import logger
from omu import Address

from omuserver.directories import get_directories
from omuserver.security.permission import AdminPermissions
from omuserver.server.omuserver import OmuServer


def set_output_utf8():
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")


type Coro[**P, T] = Callable[P, Coroutine[None, None, T]]


@click.command()
@click.option("--debug", is_flag=True)
@click.option("--token", type=str, default=None)
def main(debug: bool, token: str | None):
    loop = asyncio.get_event_loop()
    if debug:
        logger.warning("Debug mode enabled")
        tracemalloc.start()

    directories = get_directories()
    if debug:
        directories.plugins = (Path.cwd() / ".." / "packages" / "plugins").resolve()
    address = Address(
        host="0.0.0.0",
        port=26423,
        secure=False,
    )
    server = OmuServer(address, directories=directories, loop=loop)
    if token:
        loop.run_until_complete(
            server.security.add_permissions(token, AdminPermissions("admin"))
        )

    logger.info("Starting server...")
    server.run()


if __name__ == "__main__":
    set_output_utf8()
    main()

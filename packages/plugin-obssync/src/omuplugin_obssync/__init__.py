from omu import Plugin

from .plugin import on_start_server

plugin = Plugin(
    on_start_server=on_start_server,
)
__all__ = ["plugin"]

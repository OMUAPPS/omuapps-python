from omu import Plugin


def get_client():
    from .plugin import client

    return client


plugin = Plugin(
    get_client,
)
__all__ = ["plugin"]

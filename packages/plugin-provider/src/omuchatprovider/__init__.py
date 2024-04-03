from omu import Plugin


def get_client():
    from .chatprovider import client

    return client


plugin = Plugin(
    get_client,
    isolated=True,
)
__all__ = ["plugin"]

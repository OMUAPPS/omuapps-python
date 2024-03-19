from omu import Plugin


def get_plugin():
    from .chatprovider import client

    return Plugin(
        client,
    )


__all__ = ["get_plugin"]

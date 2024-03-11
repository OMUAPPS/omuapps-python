from omu import Plugin


def get_plugin():
    from .plugin import client

    return Plugin(
        client.omu,
    )


__all__ = ["get_plugin"]

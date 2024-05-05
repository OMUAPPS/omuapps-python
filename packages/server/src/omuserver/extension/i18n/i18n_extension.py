from omuserver.server import Server

from .permissions import (
    I18N_GET_LOCALES_PERMISSION,
    I18N_SET_LOCALES_PERMISSION,
)


class I18nExtension:
    def __init__(self, server: Server):
        server.permissions.register(
            I18N_GET_LOCALES_PERMISSION,
            I18N_SET_LOCALES_PERMISSION,
        )

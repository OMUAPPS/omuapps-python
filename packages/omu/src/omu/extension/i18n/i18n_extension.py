from __future__ import annotations

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.network.packet import PacketType

I18N_EXTENSION_TYPE = ExtensionType(
    "i18n",
    lambda client: I18nExtension(client),
    lambda: [],
)


REGISTER_I18N_PACKET = PacketType[str].create_json(I18N_EXTENSION_TYPE, "register")


class I18nExtension(Extension):
    def __init__(self, client: Client):
        self.client = client

from typing import List

from omu.client import Client
from omu.extension import Extension, ExtensionType
from omu.extension.registry import RegistryType
from omu.localization import Locale, LocalizedText

I18N_EXTENSION_TYPE = ExtensionType(
    "i18n", lambda client: I18nExtension(client), lambda: []
)

LOCALES_REGISTRY = RegistryType[List[Locale]].create_json(
    I18N_EXTENSION_TYPE, name="locales", default_value=[]
)


class I18nExtension(Extension):
    def __init__(self, client: Client):
        self.client = client
        self.locales_registry = client.registry.get(LOCALES_REGISTRY)
        self.locales: List[Locale] = []
        client.network.listeners.connected += self._handle_connected

    async def _handle_connected(self) -> None:
        self.locales = await self.locales_registry.get()

    def translate(self, localized_text: LocalizedText) -> str:
        if not self.locales:
            raise RuntimeError("Locales not loaded")
        if isinstance(localized_text, str):
            return localized_text
        translation = self.select_best_translation(localized_text)
        if not translation:
            raise ValueError(
                f"Missing translation for {self.locales} in {localized_text}"
            )
        return translation

    def select_best_translation(self, localized_text: LocalizedText) -> str | None:
        if isinstance(localized_text, str):
            return localized_text
        if not localized_text:
            return None
        if not self.locales:
            raise RuntimeError("Locales not loaded")
        translations = localized_text
        for locale in self.locales:
            translation = translations.get(locale)
            if translation:
                return translation
        translation = next(iter(translations.values()))
        return translation

from dataclasses import dataclass
from typing import Dict

from omu.identifier import Identifier

from .locale import Locale

type LocalizationData = Dict[Locale, str]
type Translation = Dict[str, Translation | LocalizationData]


foge: Translation = {
    "general": {
        "hello": {
            "en": "Hello",
            "fr": "Bonjour",
            "ja": "こんにちは",
        },
        "goodbye": {
            "en": "Goodbye",
            "fr": "Au revoir",
            "ja": "さようなら",
        },
        "aa": {
            "ja": "さようなら",
        },
    },
}


@dataclass(frozen=True)
class I18nLocalization:
    identifier: Identifier
    translations: Translation
    fallback: Locale


class Translator:
    def __init__(self, localizations: Dict[Identifier, I18nLocalization]):
        self.localizations = localizations

    def translate(self, identifier: Identifier, locale: Locale) -> str:
        localization = self.localizations.get(identifier)
        if localization is None:
            raise ValueError(f"Localization {identifier} not found")
        translation = localization.translations
        for key in identifier.path:
            translation = translation[key]
        if isinstance(translation, str):
            return translation
        translation = translation.get(locale)
        if translation is None:
            translation = translation.get(localization.fallback)
        if translation is None:
            raise ValueError(f"Translation {identifier} not found")
        return translation

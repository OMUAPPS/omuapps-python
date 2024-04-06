from typing import Mapping

from .locale import Locale

type LocalizedText = Mapping[Locale, str]
type Translations = Mapping[str, Translations | LocalizedText]

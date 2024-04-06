from typing import Mapping

from .locale import Locale

type LocalizedText = Mapping[Locale, str]
type Translations = Mapping[str, Translations | LocalizedText]


# foge: Translation = {
#     "general": {
#         "hello": {
#             "en": "Hello",
#             "fr": "Bonjour",
#             "ja": "こんにちは",
#         },
#         "goodbye": {
#             "en": "Goodbye",
#             "fr": "Au revoir",
#             "ja": "さようなら",
#         },
#         "aaaaa": {
#             "bbb": {
#                 "ja": "あああああ",
#             },
#         },
#     },
# }

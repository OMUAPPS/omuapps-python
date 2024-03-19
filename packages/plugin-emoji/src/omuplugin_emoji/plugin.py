from typing import List, Literal, TypedDict

from omu.extension.table.table import TableType
from omu.identifier import Identifier
from omu.interface.keyable import Keyable
from omu.model import Model
from omuchat import App, Client

IDENTIFIER = Identifier("cc.omuchat", "emoji")
APP = App(
    name="plugin-emoji",
    group="cc.omuchat",
    version="0.1.0",
)
client = Client(APP)


class TextPettern(TypedDict):
    type: Literal["text"]
    text: str


class ImagePettern(TypedDict):
    type: Literal["image"]
    id: str


class RegexPettern(TypedDict):
    type: Literal["regex"]
    regex: str


type Pettern = TextPettern | ImagePettern | RegexPettern


class EmojiData(TypedDict):
    id: str
    asset: str
    petterns: List[Pettern]


class Emoji(Model[EmojiData], Keyable):
    def __init__(
        self,
        id: str,
        asset: Identifier,
        petterns: List[Pettern],
    ) -> None:
        self.id = id
        self.asset = asset
        self.petterns = petterns

    def key(self) -> str:
        return self.id

    @classmethod
    def from_json(cls, json: EmojiData):
        return cls(
            json["id"],
            Identifier.from_key(json["asset"]),
            json["petterns"],
        )

    def to_json(self) -> EmojiData:
        return {
            "id": self.id,
            "asset": self.asset.key(),
            "petterns": self.petterns,
        }


EMOJI_TABLE = TableType.create_model(
    IDENTIFIER,
    name="emoji",
    model=Emoji,
)

emojis = client.tables.get(EMOJI_TABLE)


# @dataclass
# class EmojiMatch:
#     emoji: Emoji
#     match: re.Match
#     start: int
#     end: int


# def transform(component: content.Component) -> content.Component:
#     if isinstance(component, content.Text):
#         parts = transform_text_content(component)
#         if len(parts) == 1:
#             return parts[0]
#         return content.Root(parts)
#     if isinstance(component, content.Parent):
#         component.set_children(
#             [transform(sibling) for sibling in component.get_children()]
#         )
#     return component


# def transform_text_content(
#     component: content.Text,
# ) -> list[content.Component]:
#     text = component.text
#     parts = []
#     while text:
#         match: EmojiMatch | None = None
#         for emoji in emojis.cache.values():
#             if not emoji.["regex"]:
#                 continue
#             result = re.search(emoji["regex"], text)
#             if not result:
#                 continue
#             if not match or result.start() < match.start:
#                 match = EmojiMatch(emoji, result, result.start(), result.end())
#         if not match:
#             parts.append(content.Text.of(text))
#             break
#         if match.start > 0:
#             parts.append(content.Text.of(text[: match.start]))
#         parts.append(
#             content.Image.of(
#                 url=match.emoji["image_url"],
#                 id=match.emoji["id"],
#                 name=match.emoji["name"],
#             )
#         )
#         text = text[match.end :]
#     return parts


# @client.messages.proxy
# async def on_message(message: Message):
#     if not message.content:
#         return message
#     message.content = transform(message.content)
#     return message


async def main():
    await client.start()


if __name__ == "__main__":
    client.run()

import re
from dataclasses import dataclass
from typing import List, Literal, Mapping, Tuple, TypedDict

from omu.extension.table.table import TableType
from omu.identifier import Identifier
from omu.interface.keyable import Keyable
from omu.model import Model
from omuchat import App, Client
from omuchat.event.event_types import events
from omuchat.model import content
from omuchat.model.message import Message

IDENTIFIER = Identifier("cc.omuchat", "emoji", "plugin")
APP = App(
    IDENTIFIER,
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


EMOJI_TABLE_TYPE = TableType.create_model(
    IDENTIFIER,
    name="emoji",
    model=Emoji,
)
emoji_table = client.tables.get(EMOJI_TABLE_TYPE)
emoji_table.set_cache_size(1000)


class petterns:
    text: List[Tuple[TextPettern, Emoji]] = []
    image: List[Tuple[ImagePettern, Emoji]] = []
    regex: List[Tuple[RegexPettern, Emoji]] = []


@emoji_table.listen
async def update_emoji_table(items: Mapping[str, Emoji]):
    petterns.text.clear()
    petterns.image.clear()
    petterns.regex.clear()

    for emoji in items.values():
        for pettern in emoji.petterns:
            if pettern["type"] == "text":
                petterns.text.append((pettern, emoji))
            elif pettern["type"] == "image":
                petterns.image.append((pettern, emoji))
            elif pettern["type"] == "regex":
                petterns.regex.append((pettern, emoji))


@dataclass
class EmojiMatch:
    start: int
    end: int
    emoji: Emoji


def transform(component: content.Component) -> content.Component:
    if isinstance(component, content.Text):
        parts = transform_text_content(component)
        if len(parts) == 1:
            return parts[0]
        return content.Root(parts)
    if isinstance(component, content.Image):
        for pettern, emoji in petterns.image:
            if component.id == pettern["id"]:
                return content.Image.of(
                    url=client.assets.url(emoji.asset),
                    id=emoji.id,
                )
    if isinstance(component, content.Parent):
        component.set_children(
            [transform(sibling) for sibling in component.get_children()]
        )
    return component


def transform_text_content(
    component: content.Text,
) -> list[content.Component]:
    text = component.text
    parts = []
    while text:
        match = find_matching_emoji(text)
        if not match:
            parts.append(content.Text.of(text))
            break
        if match.start > 0:
            parts.append(content.Text.of(text[: match.start]))
        parts.append(
            content.Image.of(
                url=client.assets.url(match.emoji.asset),
                id=match.emoji.id,
            )
        )
        text = text[match.end :]
    return parts


def find_matching_emoji(text: str) -> EmojiMatch | None:
    match: EmojiMatch | None = None
    for pettern, asset in petterns.text:
        if match:
            search_end = match.end + len(pettern["text"])
            start = text.find(pettern["text"], None, search_end)
        else:
            start = text.find(pettern["text"])
        if start == -1:
            continue
        if not match or start < match.start:
            end = start + len(pettern["text"])
            match = EmojiMatch(start, end, asset)
        if match.start == 0:
            break
    if match:
        if match.start == 0:
            return match
        text = text[: match.start]
    for pettern, asset in petterns.regex:
        if len(pettern["regex"]) == 0:
            continue
        result = re.search(pettern["regex"], text)
        if not result:
            continue
        if not match or result.start() < match.start:
            match = EmojiMatch(result.start(), result.end(), asset)
        if match.start == 0:
            break
    return match


@client.chat.messages.proxy
async def on_message(message: Message):
    if not message.content:
        return message
    message.content = transform(message.content)
    return message


@client.on(events.ready)
async def ready():
    await emoji_table.fetch_all()


if __name__ == "__main__":
    client.run()

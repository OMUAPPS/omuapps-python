import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TypedDict

from loguru import logger
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


class EmojiConfig(TypedDict):
    active: bool


config = EmojiConfig(
    active=False,
)


@client.registry.create("config", config).listen
async def on_config_change(new_config: EmojiConfig):
    global config
    config = new_config
    logger.info(f"emoji config updated: {config}")


class TextPattern(TypedDict):
    type: Literal["text"]
    text: str


class ImagePattern(TypedDict):
    type: Literal["image"]
    id: str


class RegexPattern(TypedDict):
    type: Literal["regex"]
    regex: str


type Pattern = TextPattern | ImagePattern | RegexPattern


class EmojiData(TypedDict):
    id: str
    asset: str
    patterns: list[Pattern]


class Emoji(Model[EmojiData], Keyable):
    def __init__(
        self,
        id: str,
        asset: Identifier,
        patterns: list[Pattern],
    ) -> None:
        self.id = id
        self.asset = asset
        self.patterns = patterns

    def key(self) -> str:
        return self.id

    @classmethod
    def from_json(cls, json: EmojiData):
        return cls(
            json["id"],
            Identifier.from_key(json["asset"]),
            json["patterns"],
        )

    def to_json(self) -> EmojiData:
        return {
            "id": self.id,
            "asset": self.asset.key(),
            "patterns": self.patterns,
        }


EMOJI_TABLE_TYPE = TableType.create_model(
    IDENTIFIER,
    name="emoji",
    model_type=Emoji,
)
emoji_table = client.tables.get(EMOJI_TABLE_TYPE)
emoji_table.set_cache_size(1000)


class Patterns:
    text: list[tuple[TextPattern, Emoji]] = []
    image: list[tuple[ImagePattern, Emoji]] = []
    regex: list[tuple[RegexPattern, Emoji]] = []


@emoji_table.listen
async def update_emoji_table(items: Mapping[str, Emoji]):
    Patterns.text.clear()
    Patterns.image.clear()
    Patterns.regex.clear()

    for emoji in items.values():
        for pattern in emoji.patterns:
            if pattern["type"] == "text":
                Patterns.text.append((pattern, emoji))
            elif pattern["type"] == "image":
                Patterns.image.append((pattern, emoji))
            elif pattern["type"] == "regex":
                Patterns.regex.append((pattern, emoji))


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
        for pattern, emoji in Patterns.image:
            if component.id == pattern["id"]:
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
    for pattern, asset in Patterns.text:
        if match:
            search_end = match.end + len(pattern["text"])
            start = text.find(pattern["text"], None, search_end)
        else:
            start = text.find(pattern["text"])
        if start == -1:
            continue
        if not match or start < match.start:
            end = start + len(pattern["text"])
            match = EmojiMatch(start, end, asset)
        if match.start == 0:
            break
    if match:
        if match.start == 0:
            return match
        text = text[: match.start]
    for pattern, asset in Patterns.regex:
        if len(pattern["regex"]) == 0:
            continue
        result = re.search(pattern["regex"], text)
        if not result:
            continue
        if not match or result.start() < match.start:
            match = EmojiMatch(result.start(), result.end(), asset)
        if match.start == 0:
            break
    return match


@client.chat.messages.proxy
async def on_message(message: Message):
    if not config["active"]:
        return message
    if not message.content:
        return message
    message.content = transform(message.content)
    return message


@client.on(events.ready)
async def ready():
    await emoji_table.fetch_all()


if __name__ == "__main__":
    client.run()

import re
from dataclasses import dataclass
from typing import Dict, TypedDict

from omuchat import App, Client, Message, content

APP = App(
    name="plugin-emoji",
    group="cc.omuchat",
    version="0.1.0",
)
client = Client(APP)


class Emoji(TypedDict):
    id: str
    name: str
    image_url: str
    regex: str


class registry:
    emojis: Dict[str, Emoji] = {}


EMOJIS_REGISTRY = client.omu.registry.create("emojis", registry.emojis)


@EMOJIS_REGISTRY.listen
async def on_emojis_update(emojis: Dict[str, Emoji]) -> None:
    registry.emojis = emojis or {}


class Directories(TypedDict):
    data: str
    assets: str
    plugins: str


@dataclass
class EmojiMatch:
    emoji: Emoji
    match: re.Match
    start: int
    end: int


def transform(component: content.Component) -> content.Component:
    if isinstance(component, content.Text):
        parts = transform_text_content(component)
        if len(parts) == 1:
            return parts[0]
        return content.Root(parts)
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
        match: EmojiMatch | None = None
        for emoji in registry.emojis.values():
            if not emoji["regex"]:
                continue
            result = re.search(emoji["regex"], text)
            if not result:
                continue
            if not match or result.start() < match.start:
                match = EmojiMatch(emoji, result, result.start(), result.end())
        if not match:
            parts.append(content.Text.of(text))
            break
        if match.start > 0:
            parts.append(content.Text.of(text[: match.start]))
        parts.append(
            content.Image.of(
                url=match.emoji["image_url"],
                id=match.emoji["id"],
                name=match.emoji["name"],
            )
        )
        text = text[match.end :]
    return parts


@client.messages.proxy
async def on_message(message: Message):
    if not message.content:
        return message
    message.content = transform(message.content)
    return message


async def main():
    await client.start()


if __name__ == "__main__":
    client.run()

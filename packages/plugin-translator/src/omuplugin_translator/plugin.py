from __future__ import annotations

from typing import TypedDict

from edgetrans import EdgeTranslator, Language, Translator
from loguru import logger
from omu.identifier import Identifier
from omuchat import App, Client, content, model
from omuchat.event.event_types import events

IDENTIFIER = Identifier("cc.omuchat", "plugin-translator")
APP = App(
    IDENTIFIER,
    version="0.1.0",
)
client = Client(APP)

translator: Translator | None = None


class TrasnlatorConfig(TypedDict):
    active: bool
    language: Language


config = TrasnlatorConfig(active=False, language="ja")
CONFIG_REGISTRY_TYPE = client.registry.create("config", config)


@CONFIG_REGISTRY_TYPE.listen
async def on_config_change(new_config: TrasnlatorConfig):
    global config
    config = new_config
    logger.info(f"translator config updated: {config}")


async def translate(component: content.Component) -> content.Component:
    if not translator:
        return component
    texts = [
        sibling for sibling in component.iter() if isinstance(sibling, content.Text)
    ]
    translated = await translator.translate(
        [text.text for text in texts if text.text], config["language"]
    )
    for text, (translation, _) in zip(texts, translated):
        text.text = translation
    return component


@client.chat.messages.proxy
async def on_message_add(message: model.Message) -> model.Message:
    if not config["active"]:
        return message
    if not message.content:
        return message
    message.content = await translate(message.content)
    return message


@client.on(events.ready)
async def on_ready():
    global translator, config
    config = await CONFIG_REGISTRY_TYPE.get()
    translator = await EdgeTranslator.create()


if __name__ == "__main__":
    client.run()

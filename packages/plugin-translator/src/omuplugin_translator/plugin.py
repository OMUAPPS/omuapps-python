from __future__ import annotations

from edgetrans import EdgeTranslator, Translator
from omu.identifier import Identifier
from omuchat import App, Client, content, model
from omuchat.event.event_types import events

APP = App(
    Identifier("cc.omuchat", "plugin-translator"),
    version="0.1.0",
)
client = Client(APP)
translator: Translator | None = None


async def translate(component: content.Component) -> content.Component:
    if not translator:
        return component
    texts = [
        sibling for sibling in component.iter() if isinstance(sibling, content.Text)
    ]
    translated = await translator.translate(
        [text.text for text in texts if text.text], "ar"
    )
    for text, (translation, _) in zip(texts, translated):
        text.text = translation
    return component


@client.chat.messages.proxy
async def on_message_add(message: model.Message) -> model.Message:
    if not message.content:
        return message
    message.content = await translate(message.content)
    return message


@client.on(events.ready)
async def on_ready():
    global translator
    translator = await EdgeTranslator.create()


if __name__ == "__main__":
    client.run()

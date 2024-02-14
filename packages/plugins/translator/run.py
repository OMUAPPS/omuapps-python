from __future__ import annotations

from edgetrans import EdgeTranslator, Translator
from omuchat import App, Client, ContentComponent, TextContent, model

APP = App(
    name="translator",
    group="omu.chat.plugins",
    version="0.1.0",
)
client = Client(APP)
translator: Translator | None = None


async def translate(content: ContentComponent) -> ContentComponent:
    if not translator:
        return content
    texts = [
        sibling for sibling in content.traverse() if isinstance(sibling, TextContent)
    ]
    translated = await translator.translate(
        [text.text for text in texts if text.text], "ar"
    )
    for text, (translation, _) in zip(texts, translated):
        text.text = translation
    return content


@client.messages.proxy
async def on_message_add(message: model.Message) -> model.Message:
    if not message.content:
        return message
    message.content = await translate(message.content)
    return message


async def main():
    global translator
    translator = await EdgeTranslator.create()
    await client.start()


if __name__ == "__main__":
    client.run()

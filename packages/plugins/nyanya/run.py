from __future__ import annotations

from omuchat import App, Client, ContentComponent, TextContent, model

APP = App(
    name="nyanya",
    group="omu.chat.plugins",
    version="0.1.0",
)
client = Client(APP)
replaces = {
    "な": "にゃ",
    "ナ": "ニャ",
}


async def translate(content: ContentComponent) -> ContentComponent:
    texts = [
        sibling for sibling in content.traverse() if isinstance(sibling, TextContent)
    ]
    for text in texts:
        text.text = "".join(replaces.get(char, char) for char in text.text)
    return content


@client.messages.proxy
async def on_message_add(message: model.Message) -> model.Message:
    if not message.content:
        return message
    message.content = await translate(message.content)
    return message


async def main():
    await client.start()


if __name__ == "__main__":
    client.run()

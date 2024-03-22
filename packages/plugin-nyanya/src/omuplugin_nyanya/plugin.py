from __future__ import annotations

from omu.identifier import Identifier
from omuchat import App, Client, content, model

IDENTIFIER = Identifier("cc.omuchat", "plugin-nyanya")
APP = App(
    IDENTIFIER,
    version="0.1.0",
)
client = Client(APP)
replaces = {
    "な": "にゃ",
    "ナ": "ニャ",
}


async def translate(component: content.Component) -> content.Component:
    for child in component.iter():
        if not isinstance(child, content.Text):
            continue
        child.text = "".join(replaces.get(char, char) for char in child.text)
    return component


@client.chat.messages.proxy
async def on_message_add(message: model.Message) -> model.Message:
    if not message.content:
        return message
    message.content = await translate(message.content)
    return message


if __name__ == "__main__":
    client.run()

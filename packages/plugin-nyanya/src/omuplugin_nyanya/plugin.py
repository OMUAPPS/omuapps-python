from __future__ import annotations

from omu import App, Identifier, Omu
from omu_chat import Chat, content, model

IDENTIFIER = Identifier("com.omuapps", "plugin-nyanya")
APP = App(
    IDENTIFIER,
    version="0.1.0",
)
omu = Omu(APP)
chat = Chat(omu)
replaces = {
    "な": "にゃ",
    "ナ": "ニャ",
}


async def translate(
    component: content.Component,
) -> content.Component:
    for child in component.iter():
        if not isinstance(child, content.Text):
            continue
        child.text = child.text.translate(str.maketrans(replaces))
    return component


@chat.messages.proxy
async def on_message_add(message: model.Message) -> model.Message:
    if not message.content:
        return message
    message.content = await translate(message.content)
    return message


if __name__ == "__main__":
    omu.run()

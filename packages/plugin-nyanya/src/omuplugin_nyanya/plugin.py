from __future__ import annotations

from omuchat import App, Client, content, model

APP = App(
    name="plugin-nyanya",
    group="cc.omuchat",
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

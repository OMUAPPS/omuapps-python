from omuchat import App, Client, Message, events

client = Client(
    App(
        name="test",
        version="0.1.0",
        group="com.example",
    )
)


@client.on(events.Ready)
async def on_ready():
    print(f"We have logged in as {client.app}")


@client.on(events.MessageCreate)
async def on_message(message: Message):
    print(f"Message received: {message.text}")


if __name__ == "__main__":
    client.run()

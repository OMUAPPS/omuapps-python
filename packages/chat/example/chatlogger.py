from omuchat import App, Client, Message, events

app = App(
    "com.example:test",
    version="0.1.0",
)
client = Client(app)


@client.on(events.ready)
async def on_ready():
    print(f"We have logged in as {client.app}")


@client.on(events.message.add)
async def on_message(message: Message):
    print(f"Message received: {message.text}")


if __name__ == "__main__":
    client.run()

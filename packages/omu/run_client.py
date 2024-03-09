from omu.app import App
from omu.client import OmuClient
from omu.network import Address
from omu.network.packet import PACKET_TYPES
from omu.network.packet.packet import PacketData

address = Address(
    host="localhost",
    port=26423,
    secure=False,
)
client = OmuClient(
    app=App(
        name="test",
        group="test",
        version="0.0.1",
    ),
    address=address,
)


@client.connection.listeners.connected.subscribe
async def on_connected() -> None:
    print("Connected")


@client.connection.listeners.disconnected.subscribe
async def on_disconnected() -> None:
    print("Disconnected")


@client.connection.listeners.event.subscribe
async def on_event(event: PacketData) -> None:
    print(event)


@client.events.add_listener(PACKET_TYPES.Ready)
async def on_ready(_) -> None:
    print("Ready")


if __name__ == "__main__":
    client.run()

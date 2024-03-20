from omu.app import App
from omu.client import OmuClient
from omu.identifier import Identifier
from omu.network import Address
from omu.network.packet import PACKET_TYPES, Packet

address = Address(
    host="localhost",
    port=26423,
    secure=False,
)
IDENTIFIER = Identifier(
    "test",
    "test",
)
client = OmuClient(
    app=App(
        IDENTIFIER,
        version="0.0.1",
    ),
    address=address,
)


@client.network.listeners.connected.subscribe
async def on_connected() -> None:
    print("Connected")


@client.network.listeners.disconnected.subscribe
async def on_disconnected() -> None:
    print("Disconnected")


@client.network.listeners.packet.subscribe
async def on_event(event: Packet) -> None:
    print(event)


@client.network.add_packet_handler(PACKET_TYPES.READY)
async def on_ready(_) -> None:
    print("Ready")


if __name__ == "__main__":
    client.run()

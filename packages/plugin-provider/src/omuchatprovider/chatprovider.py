import asyncio
import time

from loguru import logger
from omu.identifier import Identifier
from omuchat import App, Channel, Client, Message, Room, events

from omuchatprovider.errors import ProviderError

from .services import ChatService, ProviderService, get_services

BASE_PROVIDER_IDENTIFIER = Identifier("cc.omuchat", "chatprovider")
APP = App(
    id=BASE_PROVIDER_IDENTIFIER,
    version="0.1.0",
)


client = Client(APP)

services: dict[Identifier, ProviderService] = {}
chat_services: dict[Identifier, ChatService] = {}

for service_class in get_services():
    service = service_class(client)
    services[service.provider.id] = service


async def register_services():
    for service in services.values():
        await client.chat.providers.add(service.provider)


async def update_channel(channel: Channel, service: ProviderService):
    try:
        if not channel.active:
            return
        fetched_rooms = await service.fetch_rooms(channel)
        for item in fetched_rooms:
            if item.room.id in chat_services:
                continue
            chat = await item.create()
            chat_services[item.room.id] = chat
            asyncio.create_task(chat.start())
            logger.info(f"Started chat for {item.room.key()}")
    except ProviderError as e:
        logger.error(f"Failed to update channel {channel.id}: {e}")


@client.on(events.channel.add)
async def on_channel_create(channel: Channel):
    provider = get_provider(channel)
    if provider is not None:
        await update_channel(channel, provider)


@client.on(events.channel.remove)
async def on_channel_remove(channel: Channel):
    provider = get_provider(channel)
    if provider is not None:
        await update_channel(channel, provider)


@client.on(events.channel.update)
async def on_channel_update(channel: Channel):
    provider = get_provider(channel)
    if provider is not None:
        await update_channel(channel, provider)


def get_provider(channel: Channel | Room) -> ProviderService | None:
    if channel.provider_id not in services:
        return None
    return services[channel.provider_id]


async def delay():
    await asyncio.sleep(15 - time.time() % 15)


async def recheck_task():
    while True:
        await recheck_channels()
        await recheck_rooms()
        await delay()


async def recheck_rooms():
    for chat in tuple(chat_services.values()):
        if chat.closed:
            del chat_services[chat.room.id]
    rooms = await client.chat.rooms.fetch_items()
    for room in filter(lambda r: r.connected, rooms.values()):
        if room.provider_id not in services:
            continue
        if not await should_remove(room, services[room.provider_id]):
            continue
        await stop_room(room)


async def stop_room(room: Room):
    room.status = "offline"
    room.connected = False
    await client.chat.rooms.update(room)
    for key, chat in tuple(chat_services.items()):
        if chat.room.key() == room.key():
            await chat.stop()
            del chat_services[key]


async def should_remove(room: Room, provider_service: ProviderService):
    if room.channel_id is None:
        return False
    channel = await client.chat.channels.get(room.channel_id)
    if channel and not channel.active:
        return True
    return not await provider_service.is_online(room)


async def recheck_channels():
    all_channels = await client.chat.channels.fetch_items()
    for channel in all_channels.values():
        provider = get_provider(channel)
        if provider is None:
            continue
        await update_channel(channel, provider)


@client.on(events.ready)
async def on_ready():
    await register_services()
    await recheck_channels()
    asyncio.create_task(recheck_task())
    logger.info("Chat provider is ready")


@client.on(events.message.add)
async def on_message_create(message: Message):
    print(f"Message created: {message.text}")
    for gift in message.gifts or []:
        print(f"Gift: {gift.name} x{gift.amount}")

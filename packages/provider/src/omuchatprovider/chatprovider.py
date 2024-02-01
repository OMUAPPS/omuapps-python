import asyncio
import time
from typing import Tuple

from loguru import logger
from omuchat import App, Channel, Client, Message, Room, events

from omuchatprovider.errors import ProviderError

from .services import ChatService, ProviderService, get_services

APP = App(
    name="provider",
    group="omu.chat",
    description="Chat provider for Omu",
    version="0.1.0",
    authors=["omu"],
    license="MIT",
    repository_url="https://github.com/OMUCHAT/provider",
)


client = Client(APP)
services: dict[str, ProviderService] = {}
chats: dict[str, Tuple[ProviderService, ChatService]] = {}


async def register_services():
    for service_cls in get_services():
        service = service_cls(client)
        services[service.info.key()] = service
        await client.providers.add(service.info)


async def update(channel: Channel, service: ProviderService):
    try:
        if channel.active:
            rooms = await service.fetch_rooms(channel)
            for url, create in rooms.items():
                if url in chats:
                    continue
                chat = await create()
                chats[url] = (service, chat)
                asyncio.create_task(chat.start())
                logger.info(f"Started chat for {url}")
        else:
            pass
    except ProviderError as e:
        logger.error(f"Failed to update channel {channel.id}: {e}")


@client.on(events.ChannelCreate)
async def on_channel_create(channel: Channel):
    service = get_provider(channel)
    if service is None:
        return
    await update(channel, service)


@client.on(events.ChannelDelete)
async def on_channel_delete(channel: Channel):
    service = get_provider(channel)
    if service is None:
        return
    await update(channel, service)


@client.on(events.ChannelUpdate)
async def on_channel_update(channel: Channel):
    service = get_provider(channel)
    if service is None:
        return
    await update(channel, service)


def get_provider(channel: Channel | Room) -> ProviderService | None:
    if channel.provider_id not in services:
        return None
    return services[channel.provider_id]


async def wait_for_delay():
    await asyncio.sleep(15 - time.time() % 15)


async def recheck_task():
    while True:
        await recheck_channels()
        await recheck_rooms()
        await wait_for_delay()


async def recheck_rooms():
    rooms = await client.rooms.fetch()
    for room in filter(lambda r: r.online, rooms.values()):
        if room.provider_id not in services:
            continue
        service = services[room.provider_id]
        if service is None:
            continue
        if await service.is_online(room):
            continue
        room.online = False
        await client.rooms.update(room)


async def recheck_channels():
    providers = await client.channels.fetch()
    for channel in providers.values():
        service = get_provider(channel)
        if service is None:
            continue
        await update(channel, service)


@client.on(events.Ready)
async def on_ready():
    await register_services()
    await recheck_channels()
    asyncio.create_task(recheck_task())
    logger.info("Ready!")


@client.on(events.MessageCreate)
async def on_message_create(message: Message):
    print(f"Message created: {message.text}")
    for gift in message.gifts or []:
        print(f"Gift: {gift.name} x{gift.amount}")

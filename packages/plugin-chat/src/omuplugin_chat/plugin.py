import re
from typing import List

import iwashi
from omu import Address, OmuClient
from omuchat import App
from omuchat.chat import (
    AUTHOR_TABLE,
    CHANNEL_TABLE,
    CHAT_PERMISSION,
    CREATE_CHANNEL_TREE_ENDPOINT,
    IDENTIFIER,
    MESSAGE_TABLE,
    PROVIDER_TABLE,
    ROOM_TABLE,
)
from omuchat.model.channel import Channel

app = App(
    IDENTIFIER,
    version="0.1.0",
)
address = Address("127.0.0.1", 26423)
client = OmuClient(app, address=address)

client.permissions.register(CHAT_PERMISSION)
messages = client.tables.get(MESSAGE_TABLE)
messages.set_permission(CHAT_PERMISSION.identifier)
messages.set_config({"cache_size": 1000})
authors = client.tables.get(AUTHOR_TABLE)
authors.set_permission(CHAT_PERMISSION.identifier)
authors.set_config({"cache_size": 500})
channels = client.tables.get(CHANNEL_TABLE)
channels.set_permission(CHAT_PERMISSION.identifier)
providers = client.tables.get(PROVIDER_TABLE)
providers.set_permission(CHAT_PERMISSION.identifier)
rooms = client.tables.get(ROOM_TABLE)
rooms.set_permission(CHAT_PERMISSION.identifier)


@client.endpoints.bind(endpoint_type=CREATE_CHANNEL_TREE_ENDPOINT)
async def create_channel_tree(url: str) -> List[Channel]:
    results = await iwashi.tree(url)
    if results is None:
        return []
    found_channels: List[Channel] = []
    services = await providers.fetch_items()
    for result in results.to_list():
        for provider in services.values():
            if provider.id == "misskey":
                continue
            if re.search(provider.regex, result.url) is None:
                continue
            found_channels.append(
                Channel(
                    provider_id=provider.id,
                    id=provider.id / result.id,
                    url=result.url,
                    name=result.name or result.id or result.service.name,
                    description=result.description or "",
                    active=True,
                    icon_url=result.profile_picture or "",
                )
            )
    return found_channels

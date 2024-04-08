import re
from typing import List

import iwashi
from omu import Address, OmuClient
from omuchat import App
from omuchat.chat import (
    AUTHOR_TABLE,
    CHANNEL_TABLE,
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


messages = client.tables.get(MESSAGE_TABLE)
authors = client.tables.get(AUTHOR_TABLE)
messages.set_config({"cache_size": 1000})
authors.set_config({"cache_size": 500})
channels = client.tables.get(CHANNEL_TABLE)
providers = client.tables.get(PROVIDER_TABLE)
rooms = client.tables.get(ROOM_TABLE)


@client.endpoints.bind(endpoint_type=CREATE_CHANNEL_TREE_ENDPOINT)
async def create_channel_tree(url: str) -> List[Channel]:
    results = await iwashi.visit(url)
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
                    provider_id=provider.key(),
                    id=result.url,
                    url=result.url,
                    name=result.title or result.site_name or result.url,
                    description=result.description or "",
                    active=True,
                    icon_url=result.profile_picture or "",
                )
            )
    return found_channels

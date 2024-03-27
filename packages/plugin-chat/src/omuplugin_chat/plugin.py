import re
from typing import List

import iwashi
from omu import Address, OmuClient
from omuchat import App
from omuchat.chat import (
    IDENTIFIER,
    AuthorsTableKey,
    ChannelsTableKey,
    CreateChannelTreeEndpoint,
    MessagesTableKey,
    ProviderTableKey,
    RoomTableKey,
)
from omuchat.model.channel import Channel

app = App(
    IDENTIFIER,
    description="",
    version="0.1.0",
    authors=["omu"],
    license="MIT",
    repository_url="https://github.com/OMUCHAT",
)
address = Address("127.0.0.1", 26423)
client = OmuClient(app, address=address)


messages = client.tables.get(MessagesTableKey)
authors = client.tables.get(AuthorsTableKey)
messages.set_config({"cache_size": 1000})
authors.set_config({"cache_size": 500})
channels = client.tables.get(ChannelsTableKey)
providers = client.tables.get(ProviderTableKey)
rooms = client.tables.get(RoomTableKey)


@client.endpoints.bind(endpoint_type=CreateChannelTreeEndpoint)
async def create_channel_tree(url: str) -> List[Channel]:
    results = await iwashi.visit(url)
    if results is None:
        return []
    channels: List[Channel] = []
    services = await providers.fetch_items()
    for result in results.to_list():
        for provider in services.values():
            if provider.id == "misskey":
                continue
            if re.search(provider.regex, result.url) is None:
                continue
            channels.append(
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
    return channels

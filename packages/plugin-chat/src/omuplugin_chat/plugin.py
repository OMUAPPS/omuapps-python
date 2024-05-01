import re

import iwashi
from omu import Address, OmuClient
from omu.extension.permission import PermissionType
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
from omuchat.permissions import (
    CHAT_CHANNEL_TREE_PERMISSION_ID,
    CHAT_PERMISSION_ID,
    CHAT_READ_PERMISSION_ID,
    CHAT_SEND_PERMISSION_ID,
    CHAT_WRITE_PERMISSION_ID,
)

app = App(
    IDENTIFIER,
    version="0.1.0",
)
address = Address("127.0.0.1", 26423)
client = OmuClient(app, address=address)

client.permissions.register(
    PermissionType(
        CHAT_PERMISSION_ID,
        metadata={
            "level": "medium",
            "name": {
                "ja": "チャットのデータ",
                "en": "Chat data",
            },
            "note": {
                "ja": "チャットデータの読み書き",
                "en": "Read and write chat data",
            },
        },
    ),
    PermissionType(
        CHAT_READ_PERMISSION_ID,
        metadata={
            "level": "low",
            "name": {
                "ja": "チャットの読み取り",
                "en": "Read chat",
            },
            "note": {
                "ja": "チャットデータの読み取り",
                "en": "Read chat data",
            },
        },
    ),
    PermissionType(
        CHAT_WRITE_PERMISSION_ID,
        metadata={
            "level": "low",
            "name": {
                "ja": "チャットの書き込み",
                "en": "Write chat",
            },
            "note": {
                "ja": "チャットデータの書き込み",
                "en": "Write chat data",
            },
        },
    ),
    PermissionType(
        CHAT_SEND_PERMISSION_ID,
        metadata={
            "level": "low",
            "name": {
                "ja": "チャットの送信",
                "en": "Send chat",
            },
            "note": {
                "ja": "チャットデータの送信",
                "en": "Send chat data",
            },
        },
    ),
    PermissionType(
        CHAT_CHANNEL_TREE_PERMISSION_ID,
        metadata={
            "level": "medium",
            "name": {
                "ja": "チャンネルツリーの作成",
                "en": "Create channel tree",
            },
            "note": {
                "ja": "チャンネルツリーの作成",
                "en": "Create channel tree",
            },
        },
    ),
)

messages = client.tables.get(MESSAGE_TABLE)
messages.set_config({"cache_size": 1000})
authors = client.tables.get(AUTHOR_TABLE)
authors.set_config({"cache_size": 500})
channels = client.tables.get(CHANNEL_TABLE)
providers = client.tables.get(PROVIDER_TABLE)
rooms = client.tables.get(ROOM_TABLE)


@client.endpoints.bind(endpoint_type=CREATE_CHANNEL_TREE_ENDPOINT)
async def create_channel_tree(url: str) -> list[Channel]:
    results = await iwashi.tree(url)
    if results is None:
        return []
    found_channels: list[Channel] = []
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

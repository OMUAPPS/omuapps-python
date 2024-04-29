from __future__ import annotations

from typing import List

from omu import Client, Identifier
from omu.extension.endpoint import EndpointType
from omu.extension.permission.permission import PermissionType
from omu.extension.table import TableType
from omu.serializer import Serializer

from omuchat.model.author import Author
from omuchat.model.channel import Channel
from omuchat.model.message import Message
from omuchat.model.provider import Provider
from omuchat.model.room import Room

IDENTIFIER = Identifier.from_key("cc.omuchat:chat")
CHAT_PERMISSION_TYPE = PermissionType(
    IDENTIFIER / "chat",
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
)
CHAT_PERMISSION = CHAT_PERMISSION_TYPE.id
CHAT_READ_PERMISSION_TYPE = PermissionType(
    IDENTIFIER / "chat" / "read",
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
)
CHAT_READ_PERMISSION = CHAT_READ_PERMISSION_TYPE.id

MESSAGE_TABLE = TableType.create_model(
    IDENTIFIER,
    "messages",
    Message,
)
AUTHOR_TABLE = TableType.create_model(
    IDENTIFIER,
    "authors",
    Author,
)
CHANNEL_TABLE = TableType.create_model(
    IDENTIFIER,
    "channels",
    Channel,
)
PROVIDER_TABLE = TableType.create_model(
    IDENTIFIER,
    "providers",
    Provider,
)
ROOM_TABLE = TableType.create_model(
    IDENTIFIER,
    "rooms",
    Room,
)
CREATE_CHANNEL_TREE_ENDPOINT = EndpointType[str, List[Channel]].create_json(
    IDENTIFIER,
    "create_channel_tree",
    response_serializer=Serializer.model(Channel).to_array(),
)


class Chat:
    def __init__(
        self,
        client: Client,
    ):
        client.server.require(IDENTIFIER)
        client.permissions.require(CHAT_PERMISSION)
        self.messages = client.tables.get(MESSAGE_TABLE)
        self.authors = client.tables.get(AUTHOR_TABLE)
        self.channels = client.tables.get(CHANNEL_TABLE)
        self.providers = client.tables.get(PROVIDER_TABLE)
        self.rooms = client.tables.get(ROOM_TABLE)

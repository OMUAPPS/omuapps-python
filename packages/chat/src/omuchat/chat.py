from __future__ import annotations

from omu import Client
from omu.extension.endpoint import EndpointType
from omu.extension.table import TablePermissions, TableType
from omu.serializer import Serializer

from omuchat.const import IDENTIFIER
from omuchat.model.author import Author
from omuchat.model.channel import Channel
from omuchat.model.message import Message
from omuchat.model.provider import Provider
from omuchat.model.room import Room
from omuchat.permissions import (
    CHAT_CHANNEL_TREE_PERMISSION_ID,
    CHAT_PERMISSION_ID,
    CHAT_READ_PERMISSION_ID,
    CHAT_WRITE_PERMISSION_ID,
)

MESSAGE_TABLE = TableType.create_model(
    IDENTIFIER,
    "messages",
    Message,
    permissions=TablePermissions(
        all=CHAT_PERMISSION_ID,
        read=CHAT_READ_PERMISSION_ID,
        write=CHAT_WRITE_PERMISSION_ID,
    ),
)
AUTHOR_TABLE = TableType.create_model(
    IDENTIFIER,
    "authors",
    Author,
    permissions=TablePermissions(
        all=CHAT_PERMISSION_ID,
        read=CHAT_READ_PERMISSION_ID,
        write=CHAT_WRITE_PERMISSION_ID,
    ),
)
CHANNEL_TABLE = TableType.create_model(
    IDENTIFIER,
    "channels",
    Channel,
    permissions=TablePermissions(
        all=CHAT_PERMISSION_ID,
        read=CHAT_READ_PERMISSION_ID,
        write=CHAT_WRITE_PERMISSION_ID,
    ),
)
PROVIDER_TABLE = TableType.create_model(
    IDENTIFIER,
    "providers",
    Provider,
    permissions=TablePermissions(
        all=CHAT_PERMISSION_ID,
        read=CHAT_READ_PERMISSION_ID,
        write=CHAT_WRITE_PERMISSION_ID,
    ),
)
ROOM_TABLE = TableType.create_model(
    IDENTIFIER,
    "rooms",
    Room,
    permissions=TablePermissions(
        all=CHAT_PERMISSION_ID,
        read=CHAT_READ_PERMISSION_ID,
        write=CHAT_WRITE_PERMISSION_ID,
    ),
)
CREATE_CHANNEL_TREE_ENDPOINT = EndpointType[str, list[Channel]].create_json(
    IDENTIFIER,
    "create_channel_tree",
    response_serializer=Serializer.model(Channel).to_array(),
    permission_id=CHAT_CHANNEL_TREE_PERMISSION_ID,
)


class Chat:
    def __init__(
        self,
        client: Client,
    ):
        client.server.require(IDENTIFIER)
        client.permissions.require(CHAT_PERMISSION_ID)
        self.messages = client.tables.get(MESSAGE_TABLE)
        self.authors = client.tables.get(AUTHOR_TABLE)
        self.channels = client.tables.get(CHANNEL_TABLE)
        self.providers = client.tables.get(PROVIDER_TABLE)
        self.rooms = client.tables.get(ROOM_TABLE)

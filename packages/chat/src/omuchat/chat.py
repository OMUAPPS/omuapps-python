from __future__ import annotations

from typing import List

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
    CHAT_PERMISSION,
    CHAT_READ_PERMISSION,
    CHAT_WRITE_PERMISSION,
)

MESSAGE_TABLE = TableType.create_model(
    IDENTIFIER,
    "messages",
    Message,
    permissions=TablePermissions(
        all=CHAT_PERMISSION,
        read=CHAT_READ_PERMISSION,
        write=CHAT_WRITE_PERMISSION,
    ),
)
AUTHOR_TABLE = TableType.create_model(
    IDENTIFIER,
    "authors",
    Author,
    permissions=TablePermissions(
        all=CHAT_PERMISSION,
        read=CHAT_READ_PERMISSION,
        write=CHAT_WRITE_PERMISSION,
    ),
)
CHANNEL_TABLE = TableType.create_model(
    IDENTIFIER,
    "channels",
    Channel,
    permissions=TablePermissions(
        all=CHAT_PERMISSION,
        read=CHAT_READ_PERMISSION,
        write=CHAT_WRITE_PERMISSION,
    ),
)
PROVIDER_TABLE = TableType.create_model(
    IDENTIFIER,
    "providers",
    Provider,
    permissions=TablePermissions(
        all=CHAT_PERMISSION,
        read=CHAT_READ_PERMISSION,
        write=CHAT_WRITE_PERMISSION,
    ),
)
ROOM_TABLE = TableType.create_model(
    IDENTIFIER,
    "rooms",
    Room,
    permissions=TablePermissions(
        all=CHAT_PERMISSION,
        read=CHAT_READ_PERMISSION,
        write=CHAT_WRITE_PERMISSION,
    ),
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

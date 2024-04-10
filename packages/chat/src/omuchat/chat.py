from __future__ import annotations

from typing import List

from omu import Client, Identifier
from omu.extension.endpoint import EndpointType
from omu.extension.table import TableType
from omu.serializer import Serializer

from omuchat.model.author import Author
from omuchat.model.channel import Channel
from omuchat.model.message import Message
from omuchat.model.provider import Provider
from omuchat.model.room import Room

IDENTIFIER = Identifier.from_key("cc.omuchat:chat")

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
        self.messages = client.tables.get(MESSAGE_TABLE)
        self.authors = client.tables.get(AUTHOR_TABLE)
        self.channels = client.tables.get(CHANNEL_TABLE)
        self.providers = client.tables.get(PROVIDER_TABLE)
        self.rooms = client.tables.get(ROOM_TABLE)

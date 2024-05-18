from __future__ import annotations

from collections.abc import Callable

from omu import Omu
from omu.extension.endpoint import EndpointType
from omu.extension.table import TablePermissions, TableType
from omu.serializer import Serializer

from omu_chat.const import IDENTIFIER
from omu_chat.event.event import EventHandler, EventRegistry, EventSource
from omu_chat.model.author import Author
from omu_chat.model.channel import Channel
from omu_chat.model.message import Message
from omu_chat.model.provider import Provider
from omu_chat.model.room import Room
from omu_chat.permissions import (
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
        omu: Omu,
    ):
        omu.server.require(IDENTIFIER)
        omu.permissions.require(CHAT_PERMISSION_ID)
        self.messages = omu.tables.get(MESSAGE_TABLE)
        self.authors = omu.tables.get(AUTHOR_TABLE)
        self.channels = omu.tables.get(CHANNEL_TABLE)
        self.providers = omu.tables.get(PROVIDER_TABLE)
        self.rooms = omu.tables.get(ROOM_TABLE)
        self.event_registry = EventRegistry(self)

    def on[**P](
        self, event: EventSource[P]
    ) -> Callable[[EventHandler[P]], EventHandler[P]]:
        def decorator(listener: EventHandler[P]) -> EventHandler[P]:
            self.event_registry.register(event, listener)
            return listener

        return decorator

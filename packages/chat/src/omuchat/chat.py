from __future__ import annotations

from typing import List, TypedDict

from omu import Client, Identifier
from omu.extension.endpoint import EndpointType
from omu.extension.table import TableType
from omu.model import Model
from omu.serializer import Serializer

from omuchat.model.author import Author, AuthorJson
from omuchat.model.channel import Channel
from omuchat.model.message import Message, MessageJson
from omuchat.model.provider import Provider
from omuchat.model.room import Room

IDENTIFIER = Identifier.from_key("cc.omuchat:chat")

MessagesTableKey = TableType.create_model(
    IDENTIFIER,
    "messages",
    Message,
)
AuthorsTableKey = TableType.create_model(
    IDENTIFIER,
    "authors",
    Author,
)
ChannelsTableKey = TableType.create_model(
    IDENTIFIER,
    "channels",
    Channel,
)
ProviderTableKey = TableType.create_model(
    IDENTIFIER,
    "providers",
    Provider,
)
RoomTableKey = TableType.create_model(
    IDENTIFIER,
    "rooms",
    Room,
)
CreateChannelTreeEndpoint = EndpointType[str, List[Channel]].create_serialized(
    IDENTIFIER,
    "create_channel_tree",
    Serializer.json(),
    Serializer.model(Channel).array().pipe(Serializer.json()),
)


MessageEventDataJson = TypedDict(
    "MessageEventDataJson", {"message": MessageJson, "author": AuthorJson}
)


class MessageEventData(
    Model[MessageEventDataJson],
):
    message: Message
    author: Author

    def to_json(self) -> MessageEventDataJson:
        return {"message": self.message.to_json(), "author": self.author.to_json()}

    @classmethod
    def from_json(cls, json):
        return cls(
            message=Message.from_json(json["message"]),
            author=Author.from_json(json["author"]),
        )


MessageEvent = EndpointType[MessageEventData, str].create_serialized(
    IDENTIFIER,
    "message",
    Serializer.model(MessageEventData).json(),
    Serializer.noop(),
)


class Chat:
    def __init__(
        self,
        client: Client,
    ):
        self.messages = client.tables.get(MessagesTableKey)
        self.authors = client.tables.get(AuthorsTableKey)
        self.channels = client.tables.get(ChannelsTableKey)
        self.providers = client.tables.get(ProviderTableKey)
        self.rooms = client.tables.get(RoomTableKey)

from __future__ import annotations

from typing import List, TypedDict

from omu import Identifier
from omu.extension.endpoint import SerializeEndpointType
from omu.extension.table import TableType
from omu.serializer import Serializer
from omu.extension.table import Model

from omuchat.model.author import Author, AuthorJson
from omuchat.model.channel import Channel
from omuchat.model.message import Message, MessageJson
from omuchat.model.provider import Provider
from omuchat.model.room import Room

IDENTIFIER = Identifier(
    name="chat",
    namespace="cc.omuchat",
)

MessagesTableKey = TableType.model(
    IDENTIFIER,
    "messages",
    Message,
)
AuthorsTableKey = TableType.model(
    IDENTIFIER,
    "authors",
    Author,
)
ChannelsTableKey = TableType.model(
    IDENTIFIER,
    "channels",
    Channel,
)
ProviderTableKey = TableType.model(
    IDENTIFIER,
    "providers",
    Provider,
)
RoomTableKey = TableType.model(
    IDENTIFIER,
    "rooms",
    Room,
)
CreateChannelTreeEndpoint = SerializeEndpointType[str, List[Channel]].of(
    IDENTIFIER,
    "create_channel_tree",
    Serializer.json(),
    Serializer.model(Channel).array().json(),
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


MessageEvent = SerializeEndpointType[MessageEventData, str].of(
    IDENTIFIER,
    "message",
    Serializer.model(MessageEventData).json(),
    Serializer.noop(),
)

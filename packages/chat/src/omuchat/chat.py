from __future__ import annotations

from typing import List, TypedDict

from omu import Identifier
from omu.extension.endpoint import SerializeEndpointType
from omu.extension.table import ModelTableType
from omu.interface import Model, Serializer

from omuchat.model.author import Author, AuthorJson
from omuchat.model.channel import Channel
from omuchat.model.message import Message, MessageJson
from omuchat.model.provider import Provider
from omuchat.model.room import Room

IDENTIFIER = Identifier(
    name="chat",
    namespace="cc.omuchat",
)

MessagesTableKey = ModelTableType.of(
    IDENTIFIER,
    "messages",
    Message,
)
MessagesTableKey.info.cache_size = 1000
AuthorsTableKey = ModelTableType.of(
    IDENTIFIER,
    "authors",
    Author,
)
AuthorsTableKey.info.cache_size = 1000
ChannelsTableKey = ModelTableType.of(
    IDENTIFIER,
    "channels",
    Channel,
)
ProviderTableKey = ModelTableType.of(
    IDENTIFIER,
    "providers",
    Provider,
)
RoomTableKey = ModelTableType.of(
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

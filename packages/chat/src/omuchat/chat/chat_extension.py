from __future__ import annotations

from typing import List, TypedDict

from omu.client import Client, ClientListener
from omu.extension import Extension, define_extension_type
from omu.extension.endpoint.endpoint import SerializeEndpointType
from omu.extension.table import TableExtensionType
from omu.extension.table.table import ModelTableType
from omu.interface import Model, Serializer

from omuchat.model.author import Author, AuthorJson
from omuchat.model.channel import Channel
from omuchat.model.message import Message, MessageJson
from omuchat.model.provider import Provider
from omuchat.model.room import Room

ChatExtensionType = define_extension_type(
    "chat", lambda client: ChatExtension(client), lambda: []
)


class ChatExtension(Extension, ClientListener):
    def __init__(self, client: Client) -> None:
        self.client = client
        client.add_listener(self)
        tables = client.extensions.get(TableExtensionType)
        self.messages = tables.get(MessagesTableKey)
        self.authors = tables.get(AuthorsTableKey)
        self.channels = tables.get(ChannelsTableKey)
        self.providers = tables.get(ProviderTableKey)
        self.rooms = tables.get(RoomTableKey)

    async def on_initialized(self) -> None:
        ...


MessagesTableKey = ModelTableType.of_extension(
    ChatExtensionType,
    "messages",
    Message,
)
MessagesTableKey.info.use_database = True
MessagesTableKey.info.cache_size = 1000
AuthorsTableKey = ModelTableType.of_extension(
    ChatExtensionType,
    "authors",
    Author,
)
AuthorsTableKey.info.use_database = True
AuthorsTableKey.info.cache_size = 1000
ChannelsTableKey = ModelTableType.of_extension(
    ChatExtensionType,
    "channels",
    Channel,
)
ProviderTableKey = ModelTableType.of_extension(
    ChatExtensionType,
    "providers",
    Provider,
)
RoomTableKey = ModelTableType.of_extension(
    ChatExtensionType,
    "rooms",
    Room,
)
CreateChannelTreeEndpoint = SerializeEndpointType[str, List[Channel]].of_extension(
    ChatExtensionType,
    "create_channel_tree",
    Serializer.noop(),
    Serializer.array(Serializer.model(Channel)),
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


MessageEvent = SerializeEndpointType[MessageEventData, str].of_extension(
    ChatExtensionType,
    "message",
    Serializer.model(MessageEventData),
    Serializer.noop(),
)

from typing import List

from omu.client import Client, ClientListener
from omu.extension import Extension, define_extension_type
from omu.extension.endpoint.endpoint import SerializeEndpointType
from omu.extension.table import TableExtensionType
from omu.extension.table.table import ModelTableType
from omu.interface import Serializer
from omuchat.model.author import Author
from omuchat.model.channel import Channel, ChannelJson
from omuchat.model.message import Message
from omuchat.model.provider import Provider, ProviderJson
from omuchat.model.room import Room, RoomJson

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
ChannelsTableKey = ModelTableType[Channel, ChannelJson].of_extension(
    ChatExtensionType,
    "channels",
    Channel,
)
ProviderTableKey = ModelTableType[Provider, ProviderJson].of_extension(
    ChatExtensionType,
    "providers",
    Provider,
)
RoomTableKey = ModelTableType[Room, RoomJson].of_extension(
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

from omuchat.model.author import Author
from omuchat.model.channel import Channel
from omuchat.model.message import Message
from omuchat.model.provider import Provider
from omuchat.model.room import Room


class EventKey[**P]:
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        if isinstance(other, EventKey):
            return self.name == other.name
        return False

    def __hash__(self):
        return hash(self.name)


class events:
    Ready = EventKey[[]]("ready")
    Disconnect = EventKey[[]]("disconnect")
    MessageCreate = EventKey[[Message]]("on_message")
    MessageUpdate = EventKey[[Message]]("on_message_update")
    MessageDelete = EventKey[[Message]]("on_message_delete")
    AuthorCreate = EventKey[[Author]]("on_author_create")
    AuthorUpdate = EventKey[[Author]]("on_author_update")
    AuthorDelete = EventKey[[Author]]("on_author_delete")
    ChannelCreate = EventKey[[Channel]]("on_channel_create")
    ChannelUpdate = EventKey[[Channel]]("on_channel_update")
    ChannelDelete = EventKey[[Channel]]("on_channel_delete")
    ProviderCreate = EventKey[[Provider]]("on_provider_create")
    ProviderUpdate = EventKey[[Provider]]("on_provider_update")
    ProviderDelete = EventKey[[Provider]]("on_provider_delete")
    RoomCreate = EventKey[[Room]]("on_room_create")
    RoomUpdate = EventKey[[Room]]("on_room_update")
    RoomDelete = EventKey[[Room]]("on_room_delete")

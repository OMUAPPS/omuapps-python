from omuchat.model import Author, Channel, Message, Provider, Room

from .event import ListenerEvent, TableEvent


class events:
    ready = ListenerEvent(lambda client: client.listeners.ready)
    message = TableEvent[Message](lambda client: client.chat.messages)
    author = TableEvent[Author](lambda client: client.chat.authors)
    channel = TableEvent[Channel](lambda client: client.chat.channels)
    provider = TableEvent[Provider](lambda client: client.chat.providers)
    room = TableEvent[Room](lambda client: client.chat.rooms)

from omuchat.client import Client
from omuchat.model.channel import Channel
from omuchat.model.provider import Provider
from omuchat.model.room import Room

from omuchatprovider.helper import get_session
from omuchatprovider.services import FetchedRoom, ProviderService

from .chat import YoutubeChatService
from .const import (
    PROVIDER,
    REACTION_PERMISSION_TYPE,
    REACTION_SIGNAL_TYPE,
    YOUTUBE_IDENTIFIER,
)
from .youtubeapi import YoutubeAPI


class YoutubeService(ProviderService):
    def __init__(self, client: Client):
        self.client = client
        self.session = get_session(PROVIDER)
        self.extractor = YoutubeAPI(client, self.session)
        self.reaction_signal = client.signal.get(REACTION_SIGNAL_TYPE)
        client.permissions.register(REACTION_PERMISSION_TYPE)

    @property
    def provider(self) -> Provider:
        return PROVIDER

    async def fetch_rooms(self, channel: Channel) -> list[FetchedRoom]:
        videos = await self.extractor.fetch_online_videos(channel.url)
        rooms: list[FetchedRoom] = []
        for video_id in videos:
            room = Room(
                provider_id=YOUTUBE_IDENTIFIER,
                id=YOUTUBE_IDENTIFIER / video_id,
                connected=False,
                status="offline",
                channel_id=channel.key(),
            )

            def create(room=room):
                return YoutubeChatService.create(self, self.client, room)

            rooms.append(
                FetchedRoom(
                    room=room,
                    create=create,
                )
            )
        return rooms

    async def is_online(self, room: Room) -> bool:
        return await self.extractor.is_online(video_id=room.id.path[-1])

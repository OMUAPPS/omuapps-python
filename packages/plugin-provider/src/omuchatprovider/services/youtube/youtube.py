from typing import List

from omuchat.client import Client
from omuchat.model.channel import Channel
from omuchat.model.provider import Provider
from omuchat.model.room import Room

from omuchatprovider.helper import get_session
from omuchatprovider.services import FetchedRoom, ProviderService

from .chat import YoutubeChatService
from .const import PROVIDER, REACTION_MESSAGE_TYPE
from .youtubeapi import YoutubeAPI


class YoutubeService(ProviderService):
    def __init__(self, client: Client):
        self.client = client
        self.session = get_session(PROVIDER)
        self.extractor = YoutubeAPI(client, self.session)
        self.reaction_message = client.message.get(REACTION_MESSAGE_TYPE)

    @property
    def provider(self) -> Provider:
        return PROVIDER

    async def fetch_rooms(self, channel: Channel) -> List[FetchedRoom]:
        videos = await self.extractor.fetch_online_videos(channel.url)
        rooms: List[FetchedRoom] = []
        for video_id in videos:
            room = Room(
                id=video_id,
                provider_id=PROVIDER.key(),
                connected=False,
                status="offline",
                channel_id=channel.key(),
            )
            rooms.append(
                FetchedRoom(
                    room=room,
                    create=lambda: YoutubeChatService.create(self, self.client, room),
                )
            )
        return rooms

    async def is_online(self, room: Room) -> bool:
        return await self.extractor.is_online(video_id=room.id)

from omu import Omu
from omu_chat import Chat
from omu_chat.model import Channel, Provider, Room

from omu_chatprovider.helper import get_session
from omu_chatprovider.services import FetchedRoom, ProviderService

from .chat import YoutubeChatService
from .const import (
    PROVIDER,
    REACTION_PERMISSION_TYPE,
    REACTION_SIGNAL_TYPE,
    YOUTUBE_IDENTIFIER,
)
from .youtubeapi import YoutubeAPI


class YoutubeService(ProviderService):
    def __init__(self, omu: Omu, chat: Chat):
        self.omu = omu
        self.chat = chat
        self.session = get_session(PROVIDER)
        self.extractor = YoutubeAPI(omu, self.session)
        self.reaction_signal = omu.signal.get(REACTION_SIGNAL_TYPE)
        omu.permissions.register(REACTION_PERMISSION_TYPE)

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
                return YoutubeChatService.create(self, self.chat, room)

            rooms.append(
                FetchedRoom(
                    room=room,
                    create=create,
                )
            )
        return rooms

    async def is_online(self, room: Room) -> bool:
        return await self.extractor.is_online(video_id=room.id.path[-1])

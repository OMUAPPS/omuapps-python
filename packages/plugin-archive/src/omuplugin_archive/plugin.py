import yt_dlp
from omu import Omu
from omu_chat import Chat, Room, events

from .const import APP

omu = Omu(APP)
chat = Chat(omu)
ytdlp = yt_dlp.YoutubeDL()


@chat.on(events.room.add)
async def on_room_add(room: Room):
    metadata = room.metadata or {}
    url = metadata.get("url")
    if url:
        info = ytdlp.extract_info(url, download=False)
        print(info)

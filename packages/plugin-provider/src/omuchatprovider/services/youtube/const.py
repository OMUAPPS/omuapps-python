from typing import Dict, TypedDict

from omu.extension.message import MessageType
from omuchat.model import Provider

from omuchatprovider.chatprovider import BASE_PROVIDER_IDENTIFIER
from omuchatprovider.helper import HTTP_REGEX

YOUTUBE_IDENTIFIER = BASE_PROVIDER_IDENTIFIER / "youtube"
YOUTUBE_URL = "https://www.youtube.com"
YOUTUBE_REGEX = (
    HTTP_REGEX
    + r"(youtu\.be\/(?P<video_id_short>[\w-]+))|(m\.)?youtube\.com\/(watch\?v=(?P<video_id>[\w_-]+|)|@(?P<channel_id_vanity>[\w_-]+|)|channel\/(?P<channel_id>[\w_-]+|)|user\/(?P<channel_id_user>[\w_-]+|)|c\/(?P<channel_id_c>[\w_-]+|))"
)
PROVIDER = Provider(
    id=YOUTUBE_IDENTIFIER,
    url="youtube.com",
    name="Youtube",
    version="0.1.0",
    repository_url="https://github.com/OMUCHAT/omuchat-python/tree/master/packages/plugin-provider/src/omuchatprovider/services/youtube",
    regex=YOUTUBE_REGEX,
)
BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
    )
}
BASE_PAYLOAD = dict(
    {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240416.05.00",
            }
        }
    }
)


class ReactionMessage(TypedDict):
    room_id: str
    reactions: Dict[str, int]


REACTION_MESSAGE_TYPE = MessageType[ReactionMessage].create_json(
    identifier=YOUTUBE_IDENTIFIER,
    name="reaction",
)

from typing import TypedDict

from omu.extension.permission import PermissionType
from omu.extension.signal import SignalPermissions, SignalType
from omuchat.model import Provider

from omuchatprovider.chatprovider import BASE_PROVIDER_IDENTIFIER
from omuchatprovider.helper import HTTP_REGEX

YOUTUBE_IDENTIFIER = BASE_PROVIDER_IDENTIFIER / "youtube"
YOUTUBE_URL = "https://www.youtube.com"
YOUTUBE_REGEX = (
    HTTP_REGEX + r"(youtu\.be\/(?P<video_id_short>[\w-]+))|(m\.)?youtube\.com\/"
    r"(watch\?v=(?P<video_id>[\w_-]+|)|@(?P<channel_id_vanity>[\w_-]+|)"
    r"|channel\/(?P<channel_id>[\w_-]+|)|user\/(?P<channel_id_user>[\w_-]+|)"
    r"|c\/(?P<channel_id_c>[\w_-]+|))"
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
BASE_PAYLOAD = {
    "context": {
        "client": {
            "clientName": "WEB",
            "clientVersion": "2.20240416.05.00",
        }
    }
}


class ReactionSignal(TypedDict):
    room_id: str
    reactions: dict[str, int]


REACTION_PERMISSION_ID = YOUTUBE_IDENTIFIER / "reaction"
REACTION_PERMISSION_TYPE = PermissionType(
    id=REACTION_PERMISSION_ID,
    metadata={
        "level": "low",
        "name": {
            "en": "Reaction",
            "ja": "リアクション",
        },
        "note": {
            "en": "Permission to get reactions from Youtube",
            "ja": "Youtubeのリアクションを取得する権限",
        },
    },
)
REACTION_SIGNAL_TYPE = SignalType[ReactionSignal].create_json(
    identifier=YOUTUBE_IDENTIFIER,
    name="reaction",
    permissions=SignalPermissions(
        all=REACTION_PERMISSION_ID,
    ),
)

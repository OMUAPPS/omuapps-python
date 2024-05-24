from typing import TypedDict

from .chatactions import ChatActions
from .contents import Continuations
from .youtuberesponse import YoutubeResponse


class LiveChatContinuation(TypedDict):
    continuations: Continuations
    actions: ChatActions
    trackingParams: str


class ContinuationContents(TypedDict):
    liveChatContinuation: LiveChatContinuation


class live_chat(YoutubeResponse):
    continuationContents: ContinuationContents

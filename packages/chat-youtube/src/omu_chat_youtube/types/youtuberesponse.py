from typing import TypedDict

from .frameworkupdates import FrameworkUpdates
from .responsecontext import ResponseContext


class YoutubeResponse(TypedDict):
    responseContext: ResponseContext
    trackingParams: str
    frameworkUpdates: FrameworkUpdates

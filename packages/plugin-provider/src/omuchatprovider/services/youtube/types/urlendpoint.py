from typing import Literal, NotRequired, TypedDict


class UrlEndpoint(TypedDict):
    url: str
    target: Literal["TARGET_NEW_WINDOW"]
    nofollow: bool


class WebCommandMetadata(TypedDict):
    ignoreNavigation: bool


class CommandMetadata(TypedDict):
    webCommandMetadata: WebCommandMetadata


class LiveChatItemContextMenuEndpoint(TypedDict):
    params: str


class ContextMenuEndpoint(TypedDict):
    commandMetadata: CommandMetadata
    liveChatItemContextMenuEndpoint: LiveChatItemContextMenuEndpoint


class NavigationEndpoint(TypedDict):
    clickTrackingParams: str
    commandMetadata: NotRequired[CommandMetadata]
    urlEndpoint: NotRequired[UrlEndpoint]

from typing import List, Literal, NotRequired, TypedDict, Union


class Param(TypedDict):
    key: str
    value: str


class ServiceTrackingParams(TypedDict):
    service: str
    params: List[Param]


class MainAppWebResponseContext(TypedDict):
    loggedOut: bool
    trackingParam: str


class WebResponseContextExtensionData(TypedDict):
    hasDecorated: bool


class ResponseContext(TypedDict):
    serviceTrackingParams: List[ServiceTrackingParams]
    mainAppWebResponseContext: MainAppWebResponseContext
    webResponseContextExtensionData: WebResponseContextExtensionData


class InvalidationId(TypedDict):
    objectSource: int
    objectId: str
    topic: str
    subscribeToGcmTopics: bool
    protoCreationTimestampMs: str


class InvalidationContinuationData(TypedDict):
    invalidationId: InvalidationId
    timeoutMs: int
    continuation: str


class Continuation(TypedDict):
    invalidationContinuationData: NotRequired[InvalidationContinuationData]


class Thumbnail(TypedDict):
    url: str
    width: int
    height: int


class Thumbnails(TypedDict):
    thumbnails: List[Thumbnail]


class AccessibilityData(TypedDict):
    label: str


class Accessibility(TypedDict):
    accessibilityData: AccessibilityData


class Image(TypedDict):
    thumbnails: List[Thumbnail]
    accessibility: Accessibility


class Emoji(TypedDict):
    emojiId: str
    shortcuts: List[str]
    searchTerms: List[str]
    image: Image
    isCustomEmoji: bool


class TextRun(TypedDict):
    text: str


class UrlEndpoint(TypedDict):
    url: str
    target: Literal["TARGET_NEW_WINDOW"]
    nofollow: bool


class WebCommandMetadata(TypedDict):
    ignoreNavigation: bool


class CommandMetadata(TypedDict):
    webCommandMetadata: WebCommandMetadata


class NavigationEndpoint(TypedDict):
    clickTrackingParams: str
    commandMetadata: NotRequired[CommandMetadata]
    urlEndpoint: NotRequired[UrlEndpoint]


class LinkRun(TypedDict):
    """{
        "text": "https://shop.hololivepro.com/products...",
        "navigationEndpoint": {
            "clickTrackingParams": "CAEQl98BIhMIpPTD9bu_hAMVqdA0Bx0ZlAlV",
            "commandMetadata": {
                "webCommandMetadata": {
                    "url": "https://www.youtube.com/redirect?event=live_chat\u0026redir_token=QUFFLUhqbnZxMDlGNUhELWo0MGNCTWRqVE00X2ZSVFRZZ3xBQ3Jtc0tuNlB5UG4waDhiZzZUcFVpNV96Y3JnczBmQ3N6b0dLRlRibnhiWmR5T1lhdzVHYXExR2dDb3hzNnZkT2VvWkFTdXFnS0sxN25EUTBwVXlPR1RNSnY2Y21BQktVS01fMlloNkhDYWdyeVhCc2JMdzJDMA\u0026q=https%3A%2F%2Fshop.hololivepro.com%2Fproducts%2Fnekomataokayu_bd2024",
                    "webPageType": "WEB_PAGE_TYPE_UNKNOWN",
                    "rootVe": 83769,
                }
            },
            "urlEndpoint": {
                "url": "https://www.youtube.com/redirect?event=live_chat\u0026redir_token=QUFFLUhqbnZxMDlGNUhELWo0MGNCTWRqVE00X2ZSVFRZZ3xBQ3Jtc0tuNlB5UG4waDhiZzZUcFVpNV96Y3JnczBmQ3N6b0dLRlRibnhiWmR5T1lhdzVHYXExR2dDb3hzNnZkT2VvWkFTdXFnS0sxN25EUTBwVXlPR1RNSnY2Y21BQktVS01fMlloNkhDYWdyeVhCc2JMdzJDMA\u0026q=https%3A%2F%2Fshop.hololivepro.com%2Fproducts%2Fnekomataokayu_bd2024",
                "target": "TARGET_NEW_WINDOW",
                "nofollow": true,
            },
        },
    }"""

    text: str
    navigationEndpoint: NotRequired[NavigationEndpoint]


class EmojiRun(TypedDict):
    emoji: Emoji


type Runs = List[Union[TextRun, LinkRun, EmojiRun]]


class Message(TypedDict):
    runs: Runs


class SimpleText(TypedDict):
    simpleText: str


class LiveChatItemContextMenuEndpoint(TypedDict):
    params: str


class ContextMenuEndpoint(TypedDict):
    commandMetadata: CommandMetadata
    liveChatItemContextMenuEndpoint: LiveChatItemContextMenuEndpoint


class Icon(TypedDict):
    iconType: Literal["OWNER", "MODERATOR"]


class LiveChatAuthorBadgeRenderer(TypedDict):
    customThumbnail: Thumbnails
    tooltip: str
    accessibility: Accessibility
    icon: NotRequired[Icon]


class AuthorBadge(TypedDict):
    liveChatAuthorBadgeRenderer: LiveChatAuthorBadgeRenderer


class ClientResource(TypedDict):
    imageName: str


class Source(TypedDict):
    clientResource: ClientResource


class Sources(TypedDict):
    sources: List[Source]


class ImageTint(TypedDict):
    color: int


class BorderImageProcessor(TypedDict):
    imageTint: ImageTint


class Processor(TypedDict):
    bprderImageProcessor: BorderImageProcessor


class UnheartedIcon(TypedDict):
    sources: List[Source]
    processor: Processor


class CreatorHeartViewModel(TypedDict):
    creatorThumbnail: Thumbnails
    heartedIcon: Sources
    unheartedIcon: UnheartedIcon
    heartedHoverText: str
    heartedAccessibilityLabel: str
    unheartedAccessibilityLabel: str
    engagementStateKey: str


class CreatorHeartButton(TypedDict):
    creatorHeartViewModel: CreatorHeartViewModel


class LiveChatMessageRenderer(TypedDict):
    id: str
    timestampUsec: str
    authorExternalChannelId: str
    authorName: SimpleText
    authorPhoto: Thumbnails
    authorBadges: List[AuthorBadge]
    message: Message


class LiveChatTextMessageRenderer(LiveChatMessageRenderer):
    id: str
    timestampUsec: str
    authorExternalChannelId: str
    authorName: SimpleText
    authorPhoto: Thumbnails
    authorBadges: List[AuthorBadge]
    message: Message
    contextMenuEndpoint: ContextMenuEndpoint
    contextMenuAccessibility: Accessibility


class LiveChatPaidMessageRenderer(LiveChatMessageRenderer):
    id: str
    timestampUsec: str
    authorName: SimpleText
    authorPhoto: Thumbnails
    purchaseAmountText: SimpleText
    message: Message
    headerBackgroundColor: int
    headerTextColor: int
    bodyBackgroundColor: int
    bodyTextColor: int
    authorExternalChannelId: str
    authorNameTextColor: int
    contextMenuEndpoint: ContextMenuEndpoint
    timestampColor: int
    contextMenuAccessibility: Accessibility
    trackingParams: str
    authorBadges: List[AuthorBadge]
    textInputBackgroundColor: int
    creatorHeartButton: CreatorHeartButton
    isV2Style: bool


class LiveChatMembershipItemRenderer(LiveChatMessageRenderer):
    headerSubtext: Message


class MessageItemData(TypedDict):
    liveChatTextMessageRenderer: NotRequired[LiveChatTextMessageRenderer]
    liveChatPaidMessageRenderer: NotRequired[LiveChatPaidMessageRenderer]
    liveChatMembershipItemRenderer: NotRequired[LiveChatMembershipItemRenderer]
    """
    {'liveChatSponsorshipsGiftRedemptionAnnouncementRenderer': {'id': 'ChwKGkNLbkE1XzZkbzRRREZSWUcxZ0FkdkhnQWlR', 'timestampUsec': '1707652687762701', 'authorExternalChannelId': 'UCbk8N1Ne5l7VtjjT89MILNg', 'authorName': {'simpleText': 'ユキ'}, 'authorPhoto': {'thumbnails': [{'url': 'https://yt4.ggpht.com/Bgfw4MWOSHMycMd0Sp9NGd5zj0dmjE_9OyORhxjn3Y8XIuAb8tl5xlCQE-hXqCTlDiTN3iFH1w=s32-c-k-c0x00ffffff-no-rj', 'width': 32, 'height': 32}, {'url': 'https://yt4.ggpht.com/Bgfw4MWOSHMycMd0Sp9NGd5zj0dmjE_9OyORhxjn3Y8XIuAb8tl5xlCQE-hXqCTlDiTN3iFH1w=s64-c-k-c0x00ffffff-no-rj', 'width': 64, 'height': 64}]}, 'message': {'runs': [{'text': 'was gifted a membership by ', 'italics': True}, {'text': 'みりんぼし', 'bold': True, 'italics': True}]}, 'contextMenuEndpoint': {'commandMetadata': {'webCommandMetadata': {'ignoreNavigation': True}}, 'liveChatItemContextMenuEndpoint': {'params': 'Q2g0S0hBb2FRMHR1UVRWZk5tUnZORkZFUmxKWlJ6Rm5RV1IyU0dkQmFWRWFLU29uQ2hoVlF5MW9UVFpaU25WT1dWWkJiVlZYZUdWSmNqbEdaVUVTQzJaQ1QyeGpSMkpDUzAxdklBSW9CRElhQ2hoVlEySnJPRTR4VG1VMWJEZFdkR3BxVkRnNVRVbE1UbWM0QWtnQVVDTSUzRA=='}}, 'contextMenuAccessibility': {'accessibilityData': {'label': 'Chat actions'}}}}
    """
    liveChatSponsorshipsGiftRedemptionAnnouncementRenderer: NotRequired[
        LiveChatTextMessageRenderer
    ]


class MessageItem(TypedDict):
    item: MessageItemData


class AddChatItemAction(TypedDict):
    addChatItemAction: MessageItem


class MarkChatItemAsDeletedActionData(TypedDict):
    deletedStateMessage: Message
    targetItemId: str


class MarkChatItemAsDeletedAction(TypedDict):
    markChatItemAsDeletedAction: MarkChatItemAsDeletedActionData


type Action = Union[AddChatItemAction, MarkChatItemAsDeletedAction]


class LiveChatContinuation(TypedDict):
    continuations: List[Continuation]
    actions: List[Action]


class ContinuationContents(TypedDict):
    liveChatContinuation: LiveChatContinuation


class Reaction(TypedDict):
    key: str
    value: int


class ReactionData(TypedDict):
    unicodeEmojiId: str
    reactionCount: int


class ReactionBucket(TypedDict):
    reactions: NotRequired[List[Reaction]]
    reactionsData: NotRequired[List[ReactionData]]


class EmojiFountainDataEntity(TypedDict):
    reactionBuckets: List[ReactionBucket]


class Payload(TypedDict):
    emojiFountainDataEntity: NotRequired[EmojiFountainDataEntity]


class Mutation(TypedDict):
    payload: Payload


class EntityBatchUpdate(TypedDict):
    mutations: List[Mutation]


class FrameworkUpdates(TypedDict):
    entityBatchUpdate: EntityBatchUpdate


class Response(TypedDict):
    responseContext: ResponseContext
    continuationContents: ContinuationContents
    frameworkUpdates: NotRequired[FrameworkUpdates]  # reactions

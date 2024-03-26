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
    accessibility: NotRequired[Accessibility]


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


type Run = Union[TextRun, LinkRun, EmojiRun]


class Runs(TypedDict):
    runs: List[Run]


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
    authorBadges: NotRequired[List[AuthorBadge]]
    message: Runs


class LiveChatTextMessageRenderer(LiveChatMessageRenderer):
    id: str
    timestampUsec: str
    authorExternalChannelId: str
    authorName: SimpleText
    authorPhoto: Thumbnails
    message: Runs
    authorBadges: NotRequired[List[AuthorBadge]]
    contextMenuEndpoint: ContextMenuEndpoint
    contextMenuAccessibility: Accessibility


class LiveChatPaidMessageRenderer(LiveChatMessageRenderer):
    id: str
    timestampUsec: str
    authorName: SimpleText
    authorPhoto: Thumbnails
    purchaseAmountText: SimpleText
    message: Runs
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
    authorBadges: NotRequired[List[AuthorBadge]]
    textInputBackgroundColor: int
    creatorHeartButton: CreatorHeartButton
    isV2Style: bool


class LiveChatPaidStickerRenderer(LiveChatMessageRenderer):
    id: str
    timestampUsec: str
    authorName: SimpleText
    authorPhoto: Thumbnails
    sticker: Image
    authorExternalChannelId: str
    authorBadges: NotRequired[List[AuthorBadge]]
    purchaseAmountText: SimpleText
    contextMenuEndpoint: ContextMenuEndpoint
    contextMenuAccessibility: Accessibility
    trackingParams: str


class LiveChatMembershipItemRenderer(LiveChatMessageRenderer):
    headerSubtext: Runs


class LiveChatSponsorshipsHeaderRenderer(TypedDict):
    """
    "liveChatSponsorshipsHeaderRenderer": {
        "authorName": {
            "simpleText": "\u267e\ufe0f\u91ce\u3046\u3055\u304e"
        },
        "authorPhoto": {
            "thumbnails": [
                {
                    "url": "https://yt4.ggpht.com/-Rp0B3c4BDQcB71RKqitQdCu2L7h3EqNNqdoqPWvRC-TguuzDUztmy1hTSpqQeEC5RLqsgn3fyw=s32-c-k-c0x00ffffff-no-rj",
                    "width": 32,
                    "height": 32
                },
                {
                    "url": "https://yt4.ggpht.com/-Rp0B3c4BDQcB71RKqitQdCu2L7h3EqNqdoqPWvRC-TguuzDUztmy1hTSpqQeEC5RLqsgn3fyw=s64-c-k-c0x00ffffff-no-rj",
                    "width": 64,
                    "height": 64
                }
            ]
        },
        "primaryText": {
            "runs": [
                {
                    "text": "Gifted ",
                    "bold": true
                },
                {
                    "text": "5",
                    "bold": true
                },
                {
                    "text": " ",
                    "bold": true
                },
                {
                    "text": "Pekora Ch. \u514e\u7530\u307a\u3053\u3089",
                    "bold": true
                },
                {
                    "text": " memberships",
                    "bold": true
                }
            ]
        },
        "authorBadges": [
            {
                "liveChatAuthorBadgeRenderer": {
                    "customThumbnail": {
                        "thumbnails": [
                            {
                                "url": "https://yt3.ggpht.com/ikjRH2-DarXi4D9rQptqzbl34YrHSkAs7Uyq41itvqRiYYcpq2zNYC2scrZ9gbXQEhBuFfOZuw=s16-c-k",
                                "width": 16,
                                "height": 16
                            },
                            {
                                "url": "https://yt3.ggpht.com/ikjRH2-DarXi4D9rQptqzbl34YrHSkAs7Uyq41itvqRiYYcpq2zNYC2scrZ9gbXQEhBuFfOZuw=s32-c-k",
                                "width": 32,
                                "height": 32
                            }
                        ]
                    },
                    "tooltip": "Member (2 months)",
                    "accessibility": {
                        "accessibilityData": {
                            "label": "Member (2 months)"
                        }
                    }
                }
            }
        ],
        "contextMenuEndpoint": {
            "clickTrackingParams": "CAUQ3MMKIhMIgbSe1t6qhAMVVkP1BR04yA_O",
            "commandMetadata": {
                "webCommandMetadata": {
                    "ignoreNavigation": true
                }
            },
            "liveChatItemContextMenuEndpoint": {
                "params": "Q2g0S0hBb2FRMDlZUlRVNFJHVnhiMUZFUm1GNlJYZG5VV1JVWjAxTFRYY2FLU29uQ2hoVlF6RkVRMlZrVW1kSFNFSmtiVGd4UlRGc2JFeG9UMUVTQ3pOa2FIRlFWRXhzTkRoQklBSW9CRElhQ2hoVlEwcGpVbnA1Umw4MVNYRkxkM1ZsZW5WNmFXUTFaVkU0QWtnQVVDUSUzRA=="
            }
        },
        "contextMenuAccessibility": {
            "accessibilityData": {
                "label": "Chat actions"
            }
        },
        "image": {
            "thumbnails": [
                {
                    "url": "https://www.gstatic.com/youtube/img/sponsorships/sponsorships_gift_purchase_announcement_artwork.png"
                }
            ]
        }
    }
    """

    authorName: SimpleText
    authorPhoto: Thumbnails
    primaryText: Runs
    authorBadges: NotRequired[List[AuthorBadge]]
    contextMenuEndpoint: ContextMenuEndpoint
    contextMenuAccessibility: Accessibility
    image: Image


class LiveChatSponsorshipsGiftPurchaseAnnouncementRendererHeader(TypedDict):
    liveChatSponsorshipsHeaderRenderer: LiveChatSponsorshipsHeaderRenderer


class LiveChatSponsorshipsGiftPurchaseAnnouncementRenderer(LiveChatMessageRenderer):
    """
    {
        "liveChatSponsorshipsGiftPurchaseAnnouncementRenderer": {
            "id": "ChwKGkNPWEU1OERlcW9RREZhekV3Z1FkVGdNS013",
            "timestampUsec": "1707910568302677",
            "authorExternalChannelId": "UCJcRzyF_5IqKwuezuzid5eQ",
            "header": {

            }
        }
    }
    """

    id: str
    timestampUsec: str
    authorExternalChannelId: str
    header: LiveChatSponsorshipsGiftPurchaseAnnouncementRendererHeader


class MessageItemData(TypedDict):
    liveChatTextMessageRenderer: NotRequired[LiveChatTextMessageRenderer]
    liveChatPaidMessageRenderer: NotRequired[LiveChatPaidMessageRenderer]
    liveChatPaidStickerRenderer: NotRequired[LiveChatPaidStickerRenderer]
    liveChatMembershipItemRenderer: NotRequired[LiveChatMembershipItemRenderer]
    liveChatSponsorshipsGiftRedemptionAnnouncementRenderer: NotRequired[
        LiveChatTextMessageRenderer
    ]
    liveChatSponsorshipsGiftPurchaseAnnouncementRenderer: NotRequired[
        LiveChatSponsorshipsGiftPurchaseAnnouncementRenderer
    ]


class MessageItem(TypedDict):
    item: MessageItemData


class AddChatItemAction(TypedDict):
    addChatItemAction: MessageItem


class MarkChatItemAsDeletedActionData(TypedDict):
    deletedStateMessage: Runs
    targetItemId: str


class MarkChatItemAsDeletedAction(TypedDict):
    markChatItemAsDeletedAction: MarkChatItemAsDeletedActionData


type ChatAction = Union[AddChatItemAction, MarkChatItemAsDeletedAction]


class LiveChatContinuation(TypedDict):
    continuations: List[Continuation]
    actions: List[ChatAction]


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


# metadata


class TimedContinuationData(TypedDict):
    continuation: str
    timeoutMs: int


class MetadataContinuation(TypedDict):
    timedContinuationData: TimedContinuationData


class VideoViewCountRenderer(TypedDict):
    viewCount: SimpleText
    extraShortViewCount: SimpleText
    unlabeledViewCountValue: SimpleText
    viewCountLabel: SimpleText
    originalViewCount: str


class ViewCount(TypedDict):
    videoViewCountRenderer: VideoViewCountRenderer


class UpdateViewershipActionData(TypedDict):
    viewCount: ViewCount


class UpdateViewershipAction(TypedDict):
    updateViewershipAction: UpdateViewershipActionData


class UpdateDateTextActionData(TypedDict):
    dateText: SimpleText


class UpdateDateTextAction(TypedDict):
    updateDateTextAction: UpdateDateTextActionData


class UpdateTitleActionData(TypedDict):
    title: Runs


class UpdateTitleAction(TypedDict):
    updateTitleAction: UpdateTitleActionData


class UpdateDescriptionActionData(TypedDict):
    description: Runs


class UpdateDescriptionAction(TypedDict):
    updateDescriptionAction: UpdateDescriptionActionData


type MetadataAction = Union[
    UpdateViewershipAction,
    UpdateDateTextAction,
    UpdateTitleAction,
    UpdateDescriptionAction,
]


class UpdatedMetadata(TypedDict):
    continuation: MetadataContinuation
    actions: List[MetadataAction]

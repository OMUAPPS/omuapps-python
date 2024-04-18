from typing import List, TypedDict

from .chatactions import ChatActions


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
    clickTrackingParams: str


class ContinuationItem(TypedDict):
    invalidationContinuationData: InvalidationContinuationData


type Continuations = List[ContinuationItem]


class LiveChatRenderer(TypedDict):
    continuations: Continuations
    actions: ChatActions


class Contents(TypedDict):
    liveChatRenderer: LiveChatRenderer

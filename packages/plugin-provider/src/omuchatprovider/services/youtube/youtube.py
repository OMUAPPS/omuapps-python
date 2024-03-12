from __future__ import annotations

import asyncio
import json
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List, TypedDict

import bs4
from loguru import logger
from omu.helper import map_optional
from omuchat.client import Client
from omuchat.model import (
    MODERATOR,
    OWNER,
    VERIFIED,
    Author,
    Channel,
    Message,
    Paid,
    Provider,
    Role,
    Room,
    RoomMetadata,
    content,
)

from ...chatprovider import client
from ...errors import ProviderError, ProviderFailed
from ...helper import HTTP_REGEX, assert_none, get_session
from ...tasks import Tasks
from .. import ChatService, ProviderService
from ..service import ChatSupplier
from .types import api

INFO = Provider(
    id="youtube",
    url="youtube.com",
    name="Youtube",
    version="0.1.0",
    repository_url="https://github.com/OMUCHAT/provider",
    description="Youtube provider",
    regex=HTTP_REGEX
    + r"(youtu\.be\/(?P<video_id_short>[\w-]+))|(m\.)?youtube\.com\/(watch\?v=(?P<video_id>[\w_-]+|)|@(?P<channel_id_vanity>[\w_-]+|)|channel\/(?P<channel_id>[\w_-]+|)|user\/(?P<channel_id_user>[\w_-]+|)|c\/(?P<channel_id_c>[\w_-]+|))",
)
session = get_session(INFO)


class ReactionEvent(TypedDict):
    room_id: str
    reactions: Dict[str, int]


REACTION_MESSAGE = client.omu.message.create("youtube-reaction", ReactionEvent)

HEADERS = {
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
                "clientVersion": "2.20230622.06.00",
            }
        }
    }
)
YOUTUBE_URL = "https://www.youtube.com"


class YoutubeService(ProviderService):
    def __init__(self, client: Client):
        self.client = client

    @property
    def info(self) -> Provider:
        return INFO

    async def fetch_rooms(self, channel: Channel) -> dict[Room, ChatSupplier]:
        match = re.search(INFO.regex, channel.url)
        if match is None:
            raise ProviderFailed("Could not match url")
        options = match.groupdict()

        video_id = options.get("video_id") or options.get("video_id_short")
        if video_id is None:
            channel_id = options.get(
                "channel_id"
            ) or await self.get_channel_id_by_vanity(
                options.get("channel_id_vanity")
                or options.get("channel_id_user")
                or options.get("channel_id_c")
            )
            if channel_id is None:
                raise ProviderFailed("Could not find channel id")
            video_id = await self.get_video_id_by_channel(channel_id)
            if video_id is None:
                raise ProviderFailed("Could not find video id")
        if not await YoutubeChat.is_online(video_id):
            return {}

        room = Room(
            id=video_id,
            provider_id=INFO.key(),
            connected=False,
            status="offline",
            channel_id=channel.key(),
        )
        return {room: lambda: YoutubeChatService.create(self.client, room)}

    async def get_channel_id_by_vanity(self, vanity: str | None) -> str | None:
        if vanity is None:
            return None
        clean_vanity = re.sub(r"[^a-zA-Z0-9_-]", "", vanity)
        if not clean_vanity:
            return None
        response = await session.get(f"{YOUTUBE_URL}/@{clean_vanity }")
        soup = bs4.BeautifulSoup(await response.text(), "html.parser")
        meta_tag = soup.select_one('meta[itemprop="identifier"]')
        if meta_tag is None:
            return None
        return meta_tag.attrs.get("content")

    async def get_video_id_by_channel(self, channel_id: str) -> str | None:
        response = await session.get(
            f"{YOUTUBE_URL}/embed/live_stream?channel={channel_id}",
            headers=HEADERS,
        )
        soup = bs4.BeautifulSoup(await response.text(), "html.parser")
        canonical_link = soup.select_one('link[rel="canonical"]')
        if canonical_link is None:
            return await self.get_video_id_by_channel_feeds(channel_id)
        href = canonical_link.attrs.get("href")
        if href is None:
            return None
        match = re.search(INFO.regex, href)
        if match is None:
            return None
        options = match.groupdict()
        return options.get("video_id") or options.get("video_id_short")

    async def get_video_id_by_channel_feeds(self, channel_id: str) -> str | None:
        response = await session.get(
            f"{YOUTUBE_URL}/feeds/videos.xml?channel_id={channel_id}",
            headers=HEADERS,
        )
        soup = bs4.BeautifulSoup(await response.text(), "xml")
        link = soup.select_one("entry link")
        if link is None:
            return None
        href = link.attrs.get("href")
        if href is None:
            return None
        match = re.search(INFO.regex, href)
        if match is None:
            return None
        options = match.groupdict()
        return options.get("video_id") or options.get("video_id_short")

    async def is_online(self, room: Room) -> bool:
        return await YoutubeChat.is_online(room.id)


class YoutubeChat:
    def __init__(self, video_id: str, api_key: str, continuation: str):
        self.video_id = video_id
        self.api_key = api_key
        self.chat_continuation = continuation
        self.metadata_continuation: str | None = None

    @classmethod
    async def from_url(cls, video_id: str):
        response = await session.get(
            f"{YOUTUBE_URL}/live_chat",
            params={"v": video_id},
            headers=HEADERS,
        )
        soup = bs4.BeautifulSoup(await response.text(), "html.parser")
        data = cls.extract_script(soup, "ytcfg.set")
        api_key = data["INNERTUBE_API_KEY"]
        continuation = cls.extract_continuation(soup)
        if continuation is None:
            raise ProviderFailed("Could not find continuation")
        return cls(video_id, api_key, continuation)

    @classmethod
    def extract_continuation(cls, soup: bs4.BeautifulSoup) -> str | None:
        initial_data = cls.extract_script(soup, 'window["ytInitialData"]')
        contents = initial_data["contents"]
        if "liveChatRenderer" not in contents:
            return None
        return contents["liveChatRenderer"]["continuations"][0][
            "invalidationContinuationData"
        ]["continuation"]

    @classmethod
    def extract_script(cls, soup: bs4.BeautifulSoup, startswith: str) -> Dict:
        for script in soup.select("script"):
            script_text = script.text.strip()
            if script_text.startswith(startswith):
                break
        else:
            raise ProviderFailed(f"Could not find {startswith}")
        data_text = script_text[script_text.index("{") : script_text.rindex("}") + 1]
        data = json.loads(data_text)
        return data

    @classmethod
    async def is_online(cls, video_id: str) -> bool:
        live_chat_params = {"v": video_id}
        live_chat_response = await session.get(
            f"{YOUTUBE_URL}/live_chat",
            params=live_chat_params,
            headers=HEADERS,
        )
        if live_chat_response.status // 100 != 2:
            return False
        soup = bs4.BeautifulSoup(await live_chat_response.text(), "html.parser")
        ytcfg_data = YoutubeChat.extract_script(soup, "ytcfg.set")
        api_key = ytcfg_data["INNERTUBE_API_KEY"]
        continuation = YoutubeChat.extract_continuation(soup)
        if continuation is None:
            return False
        live_chat_request_params = {"key": api_key}
        live_chat_request_json = {
            **BASE_PAYLOAD,
            "continuation": continuation,
        }
        live_chat_request = await session.post(
            f"{YOUTUBE_URL}/youtubei/v1/live_chat/get_live_chat",
            params=live_chat_request_params,
            json=live_chat_request_json,
            headers=HEADERS,
        )
        if live_chat_request.status // 100 != 2:
            return False
        live_chat_response_data = await live_chat_request.json()
        return "continuationContents" in live_chat_response_data

    async def fetch(self, retry: int = 3) -> api.Response:
        url = f"{YOUTUBE_URL}/youtubei/v1/live_chat/get_live_chat"
        params = {"key": self.api_key}
        json_payload = {
            **BASE_PAYLOAD,
            "continuation": self.chat_continuation,
        }

        response = await session.post(
            url,
            params=params,
            json=json_payload,
            headers=HEADERS,
        )
        if response.status // 100 != 2:
            logger.warning(
                f"Could not fetch chat: {response.status=}: {response.text()}"
            )
            if retry <= 0:
                raise ProviderFailed("Could not fetch chat: too many retries")
            logger.warning("Retrying fetch chat")
            await asyncio.sleep(1)
            return await self.fetch(retry - 1)
        if not response.headers["content-type"].startswith("application/json"):
            raise ProviderFailed(
                f"Invalid content type: {response.headers["content-type"]}"
            )
        data = await response.json()

        return data

    async def next(self) -> api.Response | None:
        data = await self.fetch()
        if "continuationContents" not in data:
            return None

        continuations = data["continuationContents"]["liveChatContinuation"].get(
            "continuations"
        )
        if continuations is None:
            return data
        continuation = continuations[0]
        if "invalidationContinuationData" not in continuation:
            return data
        self.chat_continuation = continuation["invalidationContinuationData"][
            "continuation"
        ]
        return data

    async def fetch_metadata(self) -> RoomMetadata:
        url = f"{YOUTUBE_URL}/youtubei/v1/updated_metadata"
        params = {"key": self.api_key}
        json_payload = dict(**BASE_PAYLOAD)
        if self.metadata_continuation:
            json_payload["continuation"] = self.metadata_continuation
        else:
            json_payload["videoId"] = self.video_id
        response = await session.post(
            url,
            params=params,
            json=json_payload,
            headers=HEADERS,
        )
        data: api.UpdatedMetadata = await response.json()
        self.metadata_continuation = (
            data.get("continuation", {})
            .get("timedContinuationData", {})
            .get("continuation", {})
        )
        viewer_count: int | None = None
        title: content.Component | None = None
        description: content.Component | None = None
        for action in data.get("actions", []):
            if "updateViewershipAction" in action:
                update_viewership = action["updateViewershipAction"]
                view_count_data = update_viewership["viewCount"]
                video_view_count_data = view_count_data["videoViewCountRenderer"]
                viewer_count = int(video_view_count_data["originalViewCount"])
            if "updateTitleAction" in action:
                title = _parse_runs(action["updateTitleAction"]["title"])
            if "updateDescriptionAction" in action:
                description = _parse_runs(
                    action["updateDescriptionAction"]["description"]
                )
        metadata = RoomMetadata()
        if viewer_count:
            metadata["viewers"] = viewer_count
        if title:
            metadata["title"] = str(title)
        if description:
            metadata["description"] = str(description)
        return metadata


class YoutubeChatService(ChatService):
    def __init__(
        self,
        client: Client,
        room: Room,
        chat: YoutubeChat,
    ):
        self.client = client
        self._room = room
        self.chat = chat
        self.tasks = Tasks(client.loop)
        self._closed = False

    @property
    def room(self) -> Room:
        return self._room

    @property
    def closed(self) -> bool:
        return self._closed

    @classmethod
    async def get_metadata(cls, video_id: str) -> RoomMetadata:
        response = await session.get(
            f"{YOUTUBE_URL}/watch?v={video_id}",
            headers=HEADERS,
        )
        if response.status // 100 != 2:
            raise ProviderFailed(f"Could not fetch video: {response.status=}")
        soup = bs4.BeautifulSoup(await response.text(), "html.parser")
        title = assert_none(
            soup.select_one('meta[property="og:title"]'),
            "Could not find title",
        ).attrs["content"]
        description = assert_none(
            soup.select_one('meta[property="og:description"]'),
            "Could not find description",
        ).attrs["content"]
        thumbnail = assert_none(
            soup.select_one('meta[property="og:image"]'),
            "Could not find thumbnail",
        ).attrs["content"]
        viewers = int(
            assert_none(
                soup.select_one('meta[itemprop="interactionCount"]'),
                "Could not find viewers",
            ).attrs["content"]
        )
        created_at = datetime.strptime(
            assert_none(
                soup.select_one('meta[itemprop="datePublished"]'),
                "Could not find created_at",
            ).attrs["content"],
            "%Y-%m-%dT%H:%M:%S%z",
        ).isoformat()
        return RoomMetadata(
            url=f"{YOUTUBE_URL}/watch?v={video_id}",
            title=title,
            description=description,
            thumbnail=thumbnail,
            viewers=viewers,
            created_at=created_at,
        )

    @classmethod
    async def create(cls, client: Client, room: Room):
        room.metadata = await cls.get_metadata(room.id)
        await client.rooms.update(room)
        chat = await YoutubeChat.from_url(room.id)
        instance = cls(client, room, chat)
        await client.rooms.add(room)
        return instance

    async def start(self):
        count = 0
        try:
            self._room.connected = True
            await self.client.rooms.update(self._room)
            while True:
                chat_data = await self.chat.next()
                if chat_data is None:
                    break
                await self.process_chat_data(chat_data)
                await asyncio.sleep(1 / 3)
                if count % 10 == 0:
                    metadata = RoomMetadata()
                    if self.room.metadata:
                        metadata |= self.room.metadata
                    metadata |= await self.chat.fetch_metadata()
                    self.room.metadata = metadata
                    await self.client.rooms.update(self.room)
                count += 1
        finally:
            await self.stop()

    async def process_chat_data(self, data: api.Response):
        messages: List[Message] = []
        for action in data["continuationContents"]["liveChatContinuation"].get(
            "actions", []
        ):
            if "addChatItemAction" in action:
                messages.extend(
                    await self.process_message_item(action["addChatItemAction"]["item"])
                )
            if "markChatItemAsDeletedAction" in action:
                await self.process_deleted_item(action["markChatItemAsDeletedAction"])
        if len(messages) > 0:
            await self.client.messages.add(*messages)
        await self.process_reactions(data)

    async def process_message_item(self, item: api.MessageItemData) -> List[Message]:
        if "liveChatTextMessageRenderer" in item:
            data = item["liveChatTextMessageRenderer"]
            author = self._parse_author(data)
            message = _parse_runs(data["message"])
            created_at = self._parse_created_at(data)
            await self.client.authors.add(author)
            return [
                Message(
                    id=data["id"],
                    room_id=self._room.key(),
                    author_id=author.key(),
                    content=message,
                    created_at=created_at,
                )
            ]
        elif "liveChatPaidMessageRenderer" in item:
            data = item["liveChatPaidMessageRenderer"]
            author = self._parse_author(data)
            message = map_optional(data.get("message"), _parse_runs)
            paid = self._parse_paid(data)
            created_at = self._parse_created_at(data)
            await self.client.authors.add(author)
            return [
                Message(
                    id=data["id"],
                    room_id=self._room.key(),
                    author_id=author.key(),
                    content=message,
                    paid=paid,
                    created_at=created_at,
                )
            ]
        elif "liveChatMembershipItemRenderer" in item:
            data = item["liveChatMembershipItemRenderer"]
            author = self._parse_author(data)
            created_at = self._parse_created_at(data)
            logger.info
            component = content.System.of(_parse_runs(data["headerSubtext"]))
            await self.client.authors.add(author)
            return [
                Message(
                    id=data["id"],
                    room_id=self._room.key(),
                    author_id=author.key(),
                    content=component,
                    created_at=created_at,
                )
            ]
        # TODO: これらのメッセージを処理する
        elif "liveChatSponsorshipsGiftRedemptionAnnouncementRenderer" in item:
            """
            {'liveChatSponsorshipsGiftRedemptionAnnouncementRenderer': {'id': 'ChwKGkNLbkE1XzZkbzRRREZSWUcxZ0FkdkhnQWlR', 'timestampUsec': '1707652687762701', 'authorExternalChannelId': 'UCbk8N1Ne5l7VtjjT89MILNg', 'authorName': {'simpleText': 'ユキ'}, 'authorPhoto': {'thumbnails': [{'url': 'https://yt4.ggpht.com/Bgfw4MWOSHMycMd0Sp9NGd5zj0dmjE_9OyORhxjn3Y8XIuAb8tl5xlCQE-hXqCTlDiTN3iFH1w=s32-c-k-c0x00ffffff-no-rj', 'width': 32, 'height': 32}, {'url': 'https://yt4.ggpht.com/Bgfw4MWOSHMycMd0Sp9NGd5zj0dmjE_9OyORhxjn3Y8XIuAb8tl5xlCQE-hXqCTlDiTN3iFH1w=s64-c-k-c0x00ffffff-no-rj', 'width': 64, 'height': 64}]}, 'message': {'runs': [{'text': 'was gifted a membership by ', 'italics': True}, {'text': 'みりんぼし', 'bold': True, 'italics': True}]}, 'contextMenuEndpoint': {'commandMetadata': {'webCommandMetadata': {'ignoreNavigation': True}}, 'liveChatItemContextMenuEndpoint': {'params': 'Q2g0S0hBb2FRMHR1UVRWZk5tUnZORkZFUmxKWlJ6Rm5RV1IyU0dkQmFWRWFLU29uQ2hoVlF5MW9UVFpaU25WT1dWWkJiVlZYZUdWSmNqbEdaVUVTQzJaQ1QyeGpSMkpDUzAxdklBSW9CRElhQ2hoVlEySnJPRTR4VG1VMWJEZFdkR3BxVkRnNVRVbE1UbWM0QWtnQVVDTSUzRA=='}}, 'contextMenuAccessibility': {'accessibilityData': {'label': 'Chat actions'}}}}
            """
            data = item["liveChatSponsorshipsGiftRedemptionAnnouncementRenderer"]
            author = self._parse_author(data)
            created_at = self._parse_created_at(data)
            component = content.System.of(_parse_runs(data["message"]))
            await self.client.authors.add(author)
            return [
                Message(
                    id=data["id"],
                    room_id=self._room.key(),
                    author_id=author.key(),
                    content=component,
                    created_at=created_at,
                )
            ]
        elif "liveChatSponsorshipsGiftPurchaseAnnouncementRenderer" in item:
            """
            {'liveChatSponsorshipsGiftPurchaseAnnouncementRenderer': {'id': 'ChwKGkNPWEU1OERlcW9RREZhekV3Z1FkVGdNS013', 'timestampUsec': '1707910568302677', 'authorExternalChannelId': 'UCJcRzyF_5IqKwuezuzid5eQ', 'header': {'liveChatSponsorshipsHeaderRenderer': {'authorName': {'simpleText': '♾️野うさぎ'}, 'authorPhoto': {'thumbnails': [{'url': 'https://yt4.ggpht.com/-Rp0B3c4BDQcB71RKqitQdCu2L7h3EqNNqdoqPWvRC-TguuzDUztmy1hTSpqQeEC5RLqsgn3fyw=s32-c-k-c0x00ffffff-no-rj', 'width': 32, 'height': 32}, {'url': 'https://yt4.ggpht.com/-Rp0B3c4BDQcB71RKqitQdCu2L7h3EqNqdoqPWvRC-TguuzDUztmy1hTSpqQeEC5RLqsgn3fyw=s64-c-k-c0x00ffffff-no-rj', 'width': 64, 'height': 64}]}, 'primaryText': {'runs': [{'text': 'Gifted ', 'bold': True}, {'text': '5', 'bold': True}, {'text': ' ', 'bold': True}, {'text': 'Pekora Ch. 兎田ぺこら', 'bold': True}, {'text': ' memberships', 'bold': True}]}, 'authorBadges': [{'liveChatAuthorBadgeRenderer': {'customThumbnail': {'thumbnails': [{'url': 'https://yt3.ggpht.com/ikjRH2-DarXi4D9rQptqzbl34YrHSkAs7Uyq41itvqRiYYcpq2zNYC2scrZ9gbXQEhBuFfOZuw=s16-c-k', 'width': 16, 'height': 16}, {'url': 'https://yt3.ggpht.com/ikjRH2-DarXi4D9rQptqzbl34YrHSkAs7Uyq41itvqRiYYcpq2zNYC2scrZ9gbXQEhBuFfOZuw=s32-c-k', 'width': 32, 'height': 32}]}, 'tooltip': 'Member (2 months)', 'accessibility': {'accessibilityData': {'label': 'Member (2 months)'}}}}], 'contextMenuEndpoint': {'clickTrackingParams': 'CAUQ3MMKIhMIgbSe1t6qhAMVVkP1BR04yA_O', 'commandMetadata': {'webCommandMetadata': {'ignoreNavigation': True}}, 'liveChatItemContextMenuEndpoint': {'params': 'Q2g0S0hBb2FRMDlZUlRVNFJHVnhiMUZFUm1GNlJYZG5VV1JVWjAxTFRYY2FLU29uQ2hoVlF6RkVRMlZrVW1kSFNFSmtiVGd4UlRGc2JFeG9UMUVTQ3pOa2FIRlFWRXhzTkRoQklBSW9CRElhQ2hoVlEwcGpVbnA1Umw4MVNYRkxkM1ZsZW5WNmFXUTFaVkU0QWtnQVVDUSUzRA=='}}, 'contextMenuAccessibility': {'accessibilityData': {'label': 'Chat actions'}}, 'image': {'thumbnails': [{'url': 'https://www.gstatic.com/youtube/img/sponsorships/sponsorships_gift_purchase_announcement_artwork.png'}]}}}}}
            """
            data = item["liveChatSponsorshipsGiftPurchaseAnnouncementRenderer"]
        elif "liveChatPlaceholderItemRenderer" in item:
            """
            item["liveChatPlaceholderItemRenderer"] = {'id': 'ChwKGkNJdml3ZUg0aDRRREZSTEV3Z1FkWUlJTkNR', 'timestampUsec': '1706714981296711'}}
            """
        elif "liveChatPaidStickerRenderer" in item:
            """
            {'liveChatPaidStickerRenderer': {'id': 'ChwKGkNMWHQzNG1Dc29RREZUdmJsQWtkbDIwSWtn', 'contextMenuEndpoint': {'clickTrackingParams': 'CAIQ77sEIhMIjvfykIKyhAMV8W8PAh0tjA73', 'commandMetadata': {'webCommandMetadata': {'ignoreNavigation': True}}, 'liveChatItemContextMenuEndpoint': {'params': 'Q2g0S0hBb2FRMHhZZERNMGJVTnpiMUZFUmxSMllteEJhMlJzTWpCSmEyY2FLU29uQ2hoVlEweGZjV2huZEU5NU1HUjVNVUZuY0RoMmEzbFRVV2NTQzFkaFVWRlFlaTFKWmpoTklBSW9CRElhQ2hoVlEybEhhbEZZVDJKV1p6VjNRMG96VjNKRVZHSmhVbEU0QWtnQVVCUSUzRA=='}}, 'contextMenuAccessibility': {'accessibilityData': {'label': 'Chat actions'}}, 'timestampUsec': '1708160603335775', 'authorPhoto': {'thumbnails': [{'url': 'https://yt4.ggpht.com/6kb67OyfasuRvwameqsKtZidxDl6bU7PGVFL1M5i9yWX9r_gYDC3BDWzhD5C-1ImKrWYHsdaEg=s32-c-k-c0x00ffffff-no-rj', 'width': 32, 'height': 32}, {'url': 'https://yt4.ggpht.com/6kb67OyfasuRvwameqsKtZidxDl6bU7PGVFL1M5i9yWX9r_gYDC3BDWzhD5C-1ImKrWYHsdaEg=s64-c-k-c0x00ffffff-no-rj', 'width': 64, 'height': 64}]}, 'authorName': {'simpleText': 'UntitledOne'}, 'authorExternalChannelId': 'UCiGjQXObVg5wCJ3WrDTbaRQ', 'sticker': {'thumbnails': [{'url': '//lh3.googleusercontent.com/sE214N2V_KPOY00qwan1wn1xnI3Rf1OzEtA9T_iImdoS7toVw8PWMS_4YH7gS975SgCxiATt6jxgp-YJ830=s32-rp', 'width': 32, 'height': 32}, {'url': '//lh3.googleusercontent.com/sE214N2V_KPOY00qwan1wn1xnI3Rf1OzEtA9T_iImdoS7toVw8PWMS_4YH7gS975SgCxiATt6jxgp-YJ830=s64-rp', 'width': 64, 'height': 64}], 'accessibility': {'accessibilityData': {'label': '100 underlined twice'}}}, 'authorBadges': [{'liveChatAuthorBadgeRenderer': {'customThumbnail': {'thumbnails': [{'url': 'https://yt3.ggpht.com/F0YU4PUesWXUyOENvw51yhHC75hBmpbw0Xe0cJEn54xZeeVoeXTmvjNNa612Uz5BuF7Bd5DGZg=s16-c-k', 'width': 16, 'height': 16}, {'url': 'https://yt3.ggpht.com/F0YU4PUesWXUyOENvw51yhHC75hBmpbw0Xe0cJEn54xZeeVoeXTmvjNNa612Uz5BuF7Bd5DGZg=s32-c-k', 'width': 32, 'height': 32}]}, 'tooltip': 'Member (1 year)', 'accessibility': {'accessibilityData': {'label': 'Member (1 year)'}}}}], 'moneyChipBackgroundColor': 4280191205, 'moneyChipTextColor': 4294967295, 'purchaseAmountText': {'simpleText': '$0.99'}, 'stickerDisplayWidth': 32, 'stickerDisplayHeight': 32, 'backgroundColor': 4280191205, 'authorNameTextColor': 3019898879, 'trackingParams': 'CAIQ77sEIhMIjvfykIKyhAMV8W8PAh0tjA73', 'isV2Style': True}}
            """
        else:
            raise ProviderError(f"Unknown message type: {list(item.keys())} {item=}")
        return []

    async def process_deleted_item(self, item: api.MarkChatItemAsDeletedActionData):
        message = await self.client.messages.get(
            f"{self._room.key()}#{item["targetItemId"]}"
        )
        if message:
            await self.client.messages.remove(message)

    async def process_reactions(self, data: api.Response):
        if "frameworkUpdates" not in data:
            return
        reaction_counts: Counter[str] = Counter()
        for update in data["frameworkUpdates"]["entityBatchUpdate"]["mutations"]:
            payload = update.get("payload")
            if not payload or "emojiFountainDataEntity" not in payload:
                continue
            emoji_data = payload["emojiFountainDataEntity"]
            for bucket in emoji_data["reactionBuckets"]:
                reaction_counts.update(
                    {
                        reaction["key"]: reaction["value"]
                        for reaction in bucket.get("reactions", [])
                    }
                )
                reaction_counts.update(
                    {
                        reaction["unicodeEmojiId"]: reaction["reactionCount"]
                        for reaction in bucket.get("reactionsData", [])
                    }
                )
        if not reaction_counts:
            return
        await REACTION_MESSAGE.broadcast(
            ReactionEvent(
                room_id=self._room.key(),
                reactions=dict(reaction_counts),
            ),
        )

    def _parse_author(self, message: api.LiveChatMessageRenderer) -> Author:
        name = message.get("authorName", {}).get("simpleText")
        id = message.get("authorExternalChannelId")
        avatar_url = message.get("authorPhoto", {}).get("thumbnails", [])[0].get("url")
        roles: List[Role] = []
        for badge in message.get("authorBadges", []):
            if "icon" in badge["liveChatAuthorBadgeRenderer"]:
                icon_type = badge["liveChatAuthorBadgeRenderer"]["icon"]["iconType"]
                if icon_type == "MODERATOR":
                    roles.append(MODERATOR)
                elif icon_type == "OWNER":
                    roles.append(OWNER)
                elif icon_type == "VERIFIED":
                    roles.append(VERIFIED)
                else:
                    raise ProviderFailed(f"Unknown badge type: {icon_type}")
            elif "customThumbnail" in badge["liveChatAuthorBadgeRenderer"]:
                custom_thumbnail = badge["liveChatAuthorBadgeRenderer"][
                    "customThumbnail"
                ]
                roles.append(
                    Role(
                        id=custom_thumbnail["thumbnails"][0]["url"],
                        name=badge["liveChatAuthorBadgeRenderer"]["tooltip"],
                        icon_url=custom_thumbnail["thumbnails"][0]["url"],
                        is_owner=False,
                        is_moderator=False,
                    )
                )

        return Author(
            provider_id=INFO.key(),
            id=id,
            name=name,
            avatar_url=avatar_url,
            roles=roles,
        )

    def _parse_paid(self, message: api.LiveChatPaidMessageRenderer) -> Paid:
        currency_match = re.search(
            r"[^0-9]+", message["purchaseAmountText"]["simpleText"]
        )
        if currency_match is None:
            raise ProviderFailed(
                f"Could not parse currency: {message['purchaseAmountText']['simpleText']}"
            )
        currency = currency_match.group(0)
        amount_match = re.search(
            r"[\d,\.]+", message["purchaseAmountText"]["simpleText"]
        )
        if amount_match is None:
            raise ProviderFailed(
                f"Could not parse amount: {message['purchaseAmountText']['simpleText']}"
            )
        amount = float(amount_match.group(0).replace(",", ""))

        return Paid(
            currency=currency,
            amount=amount,
        )

    def _parse_created_at(self, message: api.LiveChatMessageRenderer) -> datetime:
        timestamp_usec = int(message["timestampUsec"])
        return datetime.fromtimestamp(
            timestamp_usec / 1000000,
            tz=datetime.now().astimezone().tzinfo,
        )

    async def stop(self):
        self._closed = True
        self.tasks.terminate()
        self._room.connected = False
        await self.client.rooms.update(self._room)


def _parse_runs(runs: api.Runs) -> content.Component:
    root = content.Root()
    for run in runs.get("runs", []):
        if "text" in run:
            if "navigationEndpoint" in run:
                endpoint = run.get("navigationEndpoint")
                if endpoint is None:
                    root.add(content.Text.of(run["text"]))
                elif "urlEndpoint" in endpoint:
                    url = endpoint["urlEndpoint"]["url"]
                    root.add(content.Link.of(url, content.Text.of(run["text"])))
            else:
                root.add(content.Text.of(run["text"]))
        elif "emoji" in run:
            emoji = run["emoji"]
            image_url = emoji["image"]["thumbnails"][0]["url"]
            emoji_id = emoji["emojiId"]
            name = emoji["shortcuts"][0] if emoji.get("shortcuts") else None
            root.add(
                content.Image.of(
                    url=image_url,
                    id=emoji_id,
                    name=name,
                )
            )
        else:
            raise ProviderFailed(f"Unknown run: {run}")
    return root

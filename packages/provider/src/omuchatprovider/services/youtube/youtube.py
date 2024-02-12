from __future__ import annotations

import asyncio
import json
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List, TypedDict

import bs4
from omu.helper import map_optional
from omuchat.client import Client
from omuchat.model import (
    MODERATOR,
    OWNER,
    Author,
    Channel,
    Content,
    ImageContent,
    Message,
    Paid,
    Provider,
    Role,
    Room,
    RootContent,
    TextContent,
)

from ...chatprovider import client
from ...errors import ProviderError, ProviderFailed
from ...helper import HTTP_REGEX, get_session
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


REACTION_MESSAGE = client.omu.message.register("youtube-reaction", ReactionEvent)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
    )
}
YOUTUBE_URL = "https://www.youtube.com"


class YoutubeService(ProviderService):
    def __init__(self, client: Client):
        self.client = client

    @property
    def info(self) -> Provider:
        return INFO

    async def fetch_rooms(self, channel: Channel) -> dict[str, ChatSupplier]:
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
        return {
            f"{YOUTUBE_URL}/watch?v={video_id}": lambda: YoutubeChatService.create(
                self.client, channel, video_id
            )
        }

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
        match = re.search(INFO.regex, room.url)
        if match is None:
            return False
        options = match.groupdict()
        video_id = options.get("video_id") or options.get("video_id_short")
        if video_id is None:
            return False
        return await YoutubeChat.is_online(video_id)


class YoutubeChat:
    def __init__(self, api_key: str, continuation: str):
        self.api_key = api_key
        self.continuation = continuation

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
        return cls(api_key, continuation)

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
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20230622.06.00",
                }
            },
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

    async def fetch(self) -> api.Response:
        url = f"{YOUTUBE_URL}/youtubei/v1/live_chat/get_live_chat"
        params = {"key": self.api_key}
        json_payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20230622.06.00",
                }
            },
            "continuation": self.continuation,
        }

        response = await session.post(
            url,
            params=params,
            json=json_payload,
            headers=HEADERS,
        )
        if response.status // 100 != 2:
            raise ProviderFailed(f"Could not fetch chat: {response.status=}")
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
        self.continuation = continuation["invalidationContinuationData"]["continuation"]
        return data


class YoutubeChatService(ChatService):
    def __init__(
        self,
        client: Client,
        channel: Channel,
        room: Room,
        chat: YoutubeChat,
    ):
        self.client = client
        self.channel = channel
        self._room = room
        self.chat = chat
        self.tasks = Tasks(client.loop)

    @property
    def room(self) -> Room:
        return self._room

    @classmethod
    async def create(cls, client: Client, channel: Channel, video_id: str):
        room = Room(
            id=video_id,
            provider_id=INFO.key(),
            channel_id=channel.key(),
            name="Youtube",
            online=False,
            url=f"{YOUTUBE_URL}/watch?v={video_id}",
            image_url=f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        )
        chat = await YoutubeChat.from_url(video_id)
        instance = cls(client, channel, room, chat)
        await client.rooms.add(room)
        return instance

    async def start(self):
        self._room.online = True
        await self.client.rooms.update(self._room)
        while True:
            chat_data = await self.chat.next()
            if chat_data is None:
                break
            await self.process_chat_data(chat_data)
            await asyncio.sleep(1 / 3)
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
        await self.client.messages.add(*messages)
        await self.process_reactions(data)

    async def process_message_item(self, item: api.MessageItemData) -> List[Message]:
        if "liveChatTextMessageRenderer" in item:
            message = item["liveChatTextMessageRenderer"]
            author = self._parse_author(message)
            content = self._parse_message(message["message"])
            created_at = self._parse_created_at(message)
            await self.client.authors.add(author)
            return [
                Message(
                    id=message["id"],
                    room_id=self._room.key(),
                    author_id=author.key(),
                    content=content,
                    created_at=created_at,
                )
            ]
        elif "liveChatPaidMessageRenderer" in item:
            message = item["liveChatPaidMessageRenderer"]
            author = self._parse_author(message)
            content = map_optional(message.get("message"), self._parse_message)
            paid = self._parse_paid(message)
            created_at = self._parse_created_at(message)
            await self.client.authors.add(author)
            return [
                Message(
                    id=message["id"],
                    room_id=self._room.key(),
                    author_id=author.key(),
                    content=content,
                    paid=paid,
                    created_at=created_at,
                )
            ]
        elif "liveChatMembershipItemRenderer" in item:
            message = item["liveChatMembershipItemRenderer"]
            author = self._parse_author(message)
            created_at = self._parse_created_at(message)
            content = self._parse_message(
                message["headerSubtext"]
            )  # TODO: システムメッセージとして送信できるようにする。
            await self.client.authors.add(author)
            return [
                Message(
                    id=message["id"],
                    room_id=self._room.key(),
                    author_id=author.key(),
                    content=content,
                    created_at=created_at,
                )
            ]
        elif "liveChatSponsorshipsGiftRedemptionAnnouncementRenderer" in item:
            """
            {'liveChatSponsorshipsGiftRedemptionAnnouncementRenderer': {'id': 'ChwKGkNLbkE1XzZkbzRRREZSWUcxZ0FkdkhnQWlR', 'timestampUsec': '1707652687762701', 'authorExternalChannelId': 'UCbk8N1Ne5l7VtjjT89MILNg', 'authorName': {'simpleText': 'ユキ'}, 'authorPhoto': {'thumbnails': [{'url': 'https://yt4.ggpht.com/Bgfw4MWOSHMycMd0Sp9NGd5zj0dmjE_9OyORhxjn3Y8XIuAb8tl5xlCQE-hXqCTlDiTN3iFH1w=s32-c-k-c0x00ffffff-no-rj', 'width': 32, 'height': 32}, {'url': 'https://yt4.ggpht.com/Bgfw4MWOSHMycMd0Sp9NGd5zj0dmjE_9OyORhxjn3Y8XIuAb8tl5xlCQE-hXqCTlDiTN3iFH1w=s64-c-k-c0x00ffffff-no-rj', 'width': 64, 'height': 64}]}, 'message': {'runs': [{'text': 'was gifted a membership by ', 'italics': True}, {'text': 'みりんぼし', 'bold': True, 'italics': True}]}, 'contextMenuEndpoint': {'commandMetadata': {'webCommandMetadata': {'ignoreNavigation': True}}, 'liveChatItemContextMenuEndpoint': {'params': 'Q2g0S0hBb2FRMHR1UVRWZk5tUnZORkZFUmxKWlJ6Rm5RV1IyU0dkQmFWRWFLU29uQ2hoVlF5MW9UVFpaU25WT1dWWkJiVlZYZUdWSmNqbEdaVUVTQzJaQ1QyeGpSMkpDUzAxdklBSW9CRElhQ2hoVlEySnJPRTR4VG1VMWJEZFdkR3BxVkRnNVRVbE1UbWM0QWtnQVVDTSUzRA=='}}, 'contextMenuAccessibility': {'accessibilityData': {'label': 'Chat actions'}}}}
            """
        elif "liveChatPlaceholderItemRenderer" in item:
            """
            {'id': 'ChwKGkNJdml3ZUg0aDRRREZSTEV3Z1FkWUlJTkNR', 'timestampUsec': '1706714981296711'}}
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
        await self.client.omu.message.broadcast(
            REACTION_MESSAGE,
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
                else:
                    raise ProviderFailed(f"Unknown badge type: {type}")
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

    def _parse_message(self, message: api.Message) -> Content:
        runs: api.Runs = message.get("runs", [])
        root = RootContent()
        for run in runs:
            if "text" in run:
                root.add(TextContent.of(run["text"]))
            elif "emoji" in run:
                emoji = run["emoji"]
                image_url = emoji["image"]["thumbnails"][0]["url"]
                emoji_id = emoji["emojiId"]
                name = emoji["shortcuts"][0] if emoji.get("shortcuts") else None
                root.add(
                    ImageContent.of(
                        url=image_url,
                        id=emoji_id,
                        name=name,
                    )
                )
            else:
                raise ProviderFailed(f"Unknown run: {run}")
        return root

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
        self.tasks.terminate()
        self._room.online = False
        await self.client.rooms.update(self._room)

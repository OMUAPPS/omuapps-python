from __future__ import annotations

import json
import re
from typing import Any, Dict, List

import aiohttp
import bs4
from omuchat.client import Client

from omuchatprovider.errors import ProviderError
from omuchatprovider.helper import assert_none

from . import types
from .const import (
    BASE_HEADERS,
    BASE_PAYLOAD,
    YOUTUBE_REGEX,
    YOUTUBE_URL,
)


class YoutubePage:
    def __init__(
        self,
        soup: bs4.BeautifulSoup,
    ):
        self.soup = soup

    @classmethod
    async def from_response(cls, response: aiohttp.ClientResponse) -> YoutubePage:
        response_text = await response.text()
        soup = bs4.BeautifulSoup(response_text, "html.parser")
        return cls(soup)

    @property
    def ytcfg(self) -> types.ytcfg:
        ytcfg_data = self.extract_script("ytcfg.set")
        return assert_none(
            ytcfg_data,
            "Could not find ytcfg data",
        )

    @property
    def ytinitialdata(self) -> types.ytinitialdata:
        initial_data = self.extract_script('window["ytInitialData"]')
        return assert_none(
            initial_data,
            "Could not find initial data",
        )

    @property
    def INNERTUBE_API_KEY(self) -> str:
        return self.ytcfg["INNERTUBE_API_KEY"]

    def extract_script(self, prefix: str) -> Any | None:
        for script in self.soup.select("script"):
            script_text = script.text.strip()
            if script_text.startswith(prefix):
                break
        else:
            return None
        if "{" not in script_text or "}" not in script_text:
            return None
        data_text = script_text[script_text.index("{") : script_text.rindex("}") + 1]
        data = json.loads(data_text)
        return data


class YoutubeExtractor:
    def __init__(self, client: Client, session: aiohttp.ClientSession):
        self.client = client
        self.session = session

    async def get(
        self,
        url: str,
        params: Dict[str, str] | None = None,
    ) -> YoutubePage:
        response = await self.session.get(
            url,
            params=params,
            headers=BASE_HEADERS,
        )
        return await YoutubePage.from_response(response)

    async def fetch_online_videos(self, url: str) -> List[str]:
        match = assert_none(
            re.search(YOUTUBE_REGEX, url),
            "Could not match url",
        )
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
                raise ProviderError("Could not find channel id")
            video_id = await self.get_video_id_by_channel(channel_id)
            if video_id is None:
                return []
        if not await self.is_online(video_id):
            return []
        return [video_id]

    async def get_channel_id_by_vanity(self, vanity: str | None) -> str | None:
        if vanity is None:
            return None
        clean_vanity = re.sub(r"[^a-zA-Z0-9_-]", "", vanity)
        if not clean_vanity:
            return None
        response = await self.session.get(f"{YOUTUBE_URL}/@{clean_vanity }")
        soup = bs4.BeautifulSoup(await response.text(), "html.parser")
        meta_tag = soup.select_one('meta[itemprop="identifier"]')
        if meta_tag is None:
            return None
        return meta_tag.attrs.get("content")

    async def get_video_id_by_channel(self, channel_id: str) -> str | None:
        response = await self.session.get(
            f"{YOUTUBE_URL}/embed/live_stream?channel={channel_id}",
            headers=BASE_HEADERS,
        )
        soup = bs4.BeautifulSoup(await response.text(), "html.parser")
        canonical_link = soup.select_one('link[rel="canonical"]')
        if canonical_link is None:
            return await self.get_video_id_by_channel_feeds(channel_id)
        href = canonical_link.attrs.get("href")
        if href is None:
            return None
        match = re.search(YOUTUBE_REGEX, href)
        if match is None:
            return None
        options = match.groupdict()
        return options.get("video_id") or options.get("video_id_short")

    async def get_video_id_by_channel_feeds(self, channel_id: str) -> str | None:
        response = await self.session.get(
            f"{YOUTUBE_URL}/feeds/videos.xml?channel_id={channel_id}",
            headers=BASE_HEADERS,
        )
        soup = bs4.BeautifulSoup(await response.text(), "xml")
        link = soup.select_one("entry link")
        if link is None:
            return None
        href = link.attrs.get("href")
        if href is None:
            return None
        match = re.search(YOUTUBE_REGEX, href)
        if match is None:
            return None
        options = match.groupdict()
        return options.get("video_id") or options.get("video_id_short")

    async def is_online(self, video_id: str) -> bool:
        live_chat_params = {"v": video_id}
        live_chat_response = await self.session.get(
            f"{YOUTUBE_URL}/live_chat",
            params=live_chat_params,
            headers=BASE_HEADERS,
        )
        if live_chat_response.status // 100 != 2:
            return False
        response = await YoutubePage.from_response(live_chat_response)
        continuation = self.extract_continuation(response)
        if continuation is None:
            return False
        live_chat_request = await self.session.post(
            f"{YOUTUBE_URL}/youtubei/v1/live_chat/get_live_chat",
            params={
                "key": response.ytcfg["INNERTUBE_API_KEY"],
            },
            json={
                **BASE_PAYLOAD,
                "continuation": continuation,
            },
            headers=BASE_HEADERS,
        )
        if live_chat_request.status // 100 != 2:
            return False
        live_chat_response_data = await live_chat_request.json()
        return "continuationContents" in live_chat_response_data

    @classmethod
    def extract_continuation(cls, youtube_response: YoutubePage) -> str | None:
        initial_data = youtube_response.extract_script('window["ytInitialData"]')
        if initial_data is None:
            return None
        contents = initial_data["contents"]
        if "liveChatRenderer" not in contents:
            return None
        return contents["liveChatRenderer"]["continuations"][0][
            "invalidationContinuationData"
        ]["continuation"]

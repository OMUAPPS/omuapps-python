from __future__ import annotations

import asyncio
from typing import Dict, List, Set, TypedDict

from aiohttp import web
from loguru import logger
from omu.identifier import Identifier
from omuchat import App, Client, events, model

IDENTIFIER = Identifier("cc.omuchat", "plugin-onesync")
APP = App(
    IDENTIFIER,
    version="0.1.0",
)
client = Client(APP)
app = web.Application()


class Color(TypedDict):
    r: int
    g: int
    b: int


class Badge(TypedDict):
    label: str
    url: str


class CommentData(TypedDict):
    id: str
    liveId: str
    userId: str
    name: str
    screenName: str
    hasGift: bool
    isOwner: bool
    isAnonymous: bool
    profileImage: str
    badges: List[Badge]
    timestamp: str
    comment: str
    displayName: str
    originalProfileImage: str
    isFirstTime: bool


class CommentMeta(TypedDict):
    no: int
    tc: int


class CommentServiceData(TypedDict):
    id: str
    name: str
    url: str
    write: bool
    speech: bool
    options: Dict
    enabled: bool
    persist: bool
    translate: List
    color: Color


class Comment(TypedDict):
    id: str
    service: str
    name: str
    url: str
    color: Color
    data: CommentData
    meta: CommentMeta
    serviceData: CommentServiceData


def format_content(*components: model.content.Component | None) -> str:
    if not components:
        return ""
    parts = []
    stack = [*components]
    while stack:
        component = stack.pop(0)
        if isinstance(component, model.content.Text):
            parts.append(component.text)
        elif isinstance(component, model.content.Image):
            parts.append(f'<img src="{component.url}" alt="{component.id}" />')
        elif isinstance(component, model.content.Link):
            parts.append(
                f'<a href="{component.url}">{format_content(*component.children)}</a>'
            )
        elif isinstance(component, model.content.Parent):
            stack.extend(component.get_children())
    return "".join(parts)


async def to_comment(message: model.Message) -> Comment | None:
    room = await client.chat.rooms.get(message.room_id)
    author = message.author_id and await client.chat.authors.get(message.author_id)
    if not room or not author:
        return None
    metadata = room.metadata or {}
    badges = []
    for badge in author.roles:
        if badge.icon_url:
            badges.append(
                Badge(
                    label=badge.name,
                    url=badge.icon_url,
                )
            )
    return Comment(
        id=room.key(),
        service=room.provider_id,
        name=metadata.get("title", ""),
        url=metadata.get("url", ""),
        color={"r": 190, "g": 44, "b": 255},
        data=CommentData(
            id=message.key(),
            liveId=room.id,
            userId=author.key(),
            name=author.name,
            screenName=author.name,
            hasGift=False,
            isOwner=False,
            isAnonymous=False,
            profileImage=author.avatar_url or "",
            badges=badges,
            timestamp=message.created_at and message.created_at.isoformat() or "",
            comment=format_content(message.content),
            displayName=author.name,
            originalProfileImage=author.avatar_url or "",
            isFirstTime=False,
        ),
        meta={"no": 1, "tc": 1},
        serviceData=CommentServiceData(
            id=room.key(),
            name=metadata.get("title", ""),
            url=metadata.get("url", ""),
            write=True,
            speech=False,
            options={},
            enabled=False,
            persist=False,
            translate=[],
            color={"r": 190, "g": 44, "b": 255},
        ),
    )


class CommentsData(TypedDict):
    comments: List[Comment]


sessions: Set[web.WebSocketResponse] = set()


async def handle(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    messages = [
        await to_comment(message)
        for message in (await client.chat.messages.fetch_items(before=35)).values()
    ]

    await ws.send_json(
        {
            "type": "connected",
            "data": CommentsData(comments=[message for message in messages if message]),
        }
    )
    sessions.add(ws)
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                pass
            elif msg.type == web.WSMsgType.ERROR:
                logger.error("ws connection closed with exception %s", ws.exception())
    finally:
        sessions.remove(ws)
    return ws


@client.on(events.message.add)
async def on_message_add(message: model.Message) -> None:
    comment = await to_comment(message)
    if not comment:
        return
    for ws in sessions:
        await ws.send_json(
            {
                "type": "comments",
                "data": CommentsData(
                    comments=[comment],
                ),
            }
        )


@client.on(events.message.update)
async def on_message_update(message: model.Message) -> None:
    comment = await to_comment(message)
    if comment is None:
        return
    for ws in sessions:
        await ws.send_json(
            {
                "type": "comments",
                "data": CommentsData(
                    comments=[comment],
                ),
            }
        )


@client.on(events.message.remove)
async def on_message_delete(message: model.Message) -> None:
    for ws in sessions:
        await ws.send_json({"type": "deleted", "data": [message.key()]})


@client.on(events.ready)
async def on_ready():
    app.add_routes([web.get("/sub", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 11180)
    asyncio.create_task(site.start())


if __name__ == "__main__":
    client.run()

from __future__ import annotations

import asyncio
from html import escape
from typing import TypedDict

from aiohttp import web
from loguru import logger
from omuchat import App, Client, events, model
from omuchat.model import content

from .onecomme import Badge, Comment, CommentData, CommentServiceData

APP = App(
    "cc.omuchat:onecomme/plugin",
    version="0.1.0",
)
client = Client(APP)
app = web.Application()


def format_content(*components: content.Component | None) -> str:
    if components is None:
        return ""
    if len(components) == 0:
        return ""
    parts = []
    stack = [*components]
    while stack:
        component = stack.pop(0)
        if isinstance(component, content.Text):
            parts.append(escape(component.text))
        elif isinstance(component, content.Image):
            parts.append(
                f'<img src="{escape(component.url)}" alt="{escape(component.id)}">'
            )
        elif isinstance(component, content.Link):
            parts.append(
                f'<a href="{component.url}">{format_content(*component.children)}</a>'
            )
        elif isinstance(component, content.System):
            parts.append(
                f"<div><span>{format_content(*component.get_children())}</span></div>"
            )
        elif isinstance(component, content.Parent):
            parts.append(f"<span>{format_content(*component.get_children())}</span>")
        else:
            raise ValueError(f"Unknown component type: {component}")
    return "".join(parts)


async def to_comment(message: model.Message) -> Comment | None:
    room = await client.chat.rooms.get(message.room_id.key())
    author: model.Author | None = None
    if message.author_id:
        author = await client.chat.authors.get(message.author_id.key())
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
        service=room.provider_id.key(),
        name=metadata.get("title", ""),
        url=metadata.get("url", ""),
        color={"r": 190, "g": 44, "b": 255},
        data=CommentData(
            id=message.key(),
            liveId=room.id.key(),
            userId=author.key(),
            name=author.name or "",
            screenName=author.name or "",
            hasGift=False,
            isOwner=False,
            isAnonymous=False,
            profileImage=author.avatar_url or "",
            badges=badges,
            timestamp=message.created_at and message.created_at.isoformat() or "",
            comment=format_content(message.content),
            displayName=author.name or "",
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
    comments: list[Comment]


sessions: set[web.WebSocketResponse] = set()


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

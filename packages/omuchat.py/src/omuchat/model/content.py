from __future__ import annotations

from typing import List, Literal, NotRequired, TypedDict

from omu.interface import Model

type ContentJson = TextContentJson | ImageContentJson | RootContentJson
type Content = TextContent | ImageContent | RootContent


class ContentComponentJson[T: str](TypedDict):
    type: T
    siblings: NotRequired[List[ContentJson]] | None


class ContentComponent(Model[ContentComponentJson]):
    def __init__(
        self, type: str, siblings: List[ContentComponent] | None = None
    ) -> None:
        self.type = type
        self.siblings = siblings

    @classmethod
    def from_json(cls, json: ContentJson) -> Content:
        match json["type"]:
            case "text":
                return TextContent.from_json(json)
            case "image":
                return ImageContent.from_json(json)
            case "root":
                return RootContent.from_json(json)

    def to_json(self) -> ContentComponentJson:
        return ContentComponentJson(
            type=self.type,
            siblings=[sibling.to_json() for sibling in self.siblings]
            if self.siblings
            else [],
        )


class RootContentJson(ContentComponentJson[Literal["root"]]):
    ...


class RootContent(ContentComponent, Model[RootContentJson]):
    def __init__(self, siblings: List[ContentComponent] | None = None) -> None:
        super().__init__(type="root", siblings=siblings)
        self.siblings = siblings

    def to_json(self) -> RootContentJson:
        return {
            "type": "root",
            "siblings": [sibling.to_json() for sibling in self.siblings]
            if self.siblings
            else [],
        }

    @classmethod
    def of(cls, *siblings: ContentComponent) -> RootContent:
        return cls(siblings=list(siblings))

    @classmethod
    def empty(cls) -> RootContent:
        return cls()

    @classmethod
    def from_json(cls, json: RootContentJson) -> RootContent:
        return cls(
            siblings=[
                ContentComponent.from_json(sibling)
                for sibling in json.get("siblings", []) or []
            ]
        )

    def add(self, *siblings: Content) -> RootContent:
        if self.siblings is None:
            self.siblings = []
        self.siblings.extend(siblings)
        return self

    def __str__(self) -> str:
        return "".join(str(sibling) for sibling in self.siblings or [])


class TextContentJson(ContentComponentJson[Literal["text"]]):
    text: str


class TextContent(ContentComponent, Model[TextContentJson]):
    def __init__(
        self, text: str, siblings: List[ContentComponent] | None = None
    ) -> None:
        super().__init__(type="text", siblings=siblings)
        self.text = text

    def to_json(self) -> TextContentJson:
        return {
            "type": "text",
            "text": self.text,
            "siblings": [sibling.to_json() for sibling in self.siblings]
            if self.siblings
            else [],
        }

    @classmethod
    def of(cls, text: str) -> TextContent:
        return cls(text=text)

    @classmethod
    def from_json(cls, json: TextContentJson) -> TextContent:
        return cls(text=json["text"])

    def __str__(self) -> str:
        return self.text


class ImageContentJson(ContentComponentJson[Literal["image"]]):
    url: str
    id: str
    name: NotRequired[str] | None


class ImageContent(ContentComponent, Model[ImageContentJson]):
    def __init__(
        self,
        url: str,
        id: str,
        name: str | None = None,
        siblings: List[ContentComponent] | None = None,
    ) -> None:
        super().__init__(type="image", siblings=siblings)
        self.url = url
        self.id = id
        self.name = name

    def to_json(self) -> ImageContentJson:
        return {
            "type": "image",
            "url": self.url,
            "id": self.id,
            "name": self.name,
            "siblings": [sibling.to_json() for sibling in self.siblings]
            if self.siblings
            else [],
        }

    @classmethod
    def of(cls, url: str, id: str, name: str | None = None) -> ImageContent:
        return cls(url=url, id=id, name=name)

    @classmethod
    def from_json(cls, json: ImageContentJson) -> ImageContent:
        return cls(url=json["url"], id=json["id"], name=json.get("name"))

    def __str__(self) -> str:
        return f"[{self.name}]({self.url})"

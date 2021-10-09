from __future__ import annotations

from typing import Any, Dict, List, Optional

import datetime

from ..utils import update_payload

__all__ = (
    "Embed",
    "EmbedFooter",
    "EmbedImage",
    "EmbedProvider",
    "EmbedVideo",
    "EmbedAuthor",
    "EmbedField",
)


class EmbedFooter:
    def __init__(self, *, text: str, icon_url: str = None) -> None:
        self.text = text
        self.icon_url = icon_url

    def to_dict(self) -> Dict[str, Any]:
        payload = {"text": self.text}
        update_payload(payload, icon_url=self.icon_url)

        return payload


class EmbedImage:
    def __init__(self, *, url: str, height: Optional[int] = None, width: Optional[int] = None) -> None:
        self.url = url
        self.height = height
        self.width = width

    def to_dict(self) -> Dict[str, Any]:
        payload = {"url": self.url}
        update_payload(payload, height=self.height, width=self.width)

        return payload


class EmbedVideo(EmbedImage):
    def __init__(self, *, url: str, height: int = None, width: int = None) -> None:
        super().__init__(url=url, height=height, width=width)

    def to_dict(self) -> Dict[str, Any]:
        return update_payload({}, **super().to_dict())


class EmbedProvider:
    def __init__(self, *, name: str = None, url: str = None) -> None:
        self.name = name
        self.url = url

    def to_dict(self) -> Dict[str, Any]:
        return update_payload({}, name=self.name, url=self.url)


class EmbedAuthor:
    def __init__(self, *, name: str, url: str = None, icon_url: str = None) -> None:
        self.name = name
        self.url = url
        self.icon_url = icon_url

    def to_dict(self) -> Dict[str, Any]:
        return update_payload({}, name=self.name, url=self.url, icon_url=self.icon_url)


class EmbedField:
    def __init__(self, *, name: str, value: str, inline: bool = True) -> None:
        self.name = name
        self.value = value
        self.inline = inline

    def to_dict(self) -> Dict[str, Any]:
        return update_payload({}, name=self.name, value=self.value, inline=self.inline)


class Embed:
    def __init__(
        self,
        *,
        title: str = None,
        description: str = None,
        color: int = None,
        url: str = None,
        timestamp: datetime.datetime = None,
        footer: EmbedFooter = None,
        image: EmbedImage = None,
        video: EmbedVideo = None,
        provider: EmbedProvider = None,
        author: EmbedAuthor = None,
        fields: List[EmbedField] = None
    ) -> None:
        self.title = title
        self.description = description
        self.color = color
        self.url = url
        self.timestamp = timestamp.isoformat() if timestamp is not None else timestamp
        self.footer = footer
        self.image = image
        self.video = video
        self.provider = provider
        self.author = author
        self.fields = [] if fields is None else fields

    def set_footer(self, *, text: str, icon_url: str = None) -> Embed:
        self.footer = EmbedFooter(text=text, icon_url=icon_url)
        return self

    def set_image(self, *, url: str, height: int = None, width: int = None) -> Embed:
        self.image = EmbedImage(url=url, height=height, width=width)
        return self

    def set_video(self, *, url: str, height: int = None, width: int = None) -> Embed:
        self.video = EmbedVideo(url=url, height=height, width=width)
        return self

    def set_provider(self, *, name: str = None, url: str = None) -> Embed:
        self.provider = EmbedProvider(name=name, url=url)
        return self

    def set_author(self, *, name: str, url: str = None, icon_url: str = None) -> Embed:
        self.author = EmbedAuthor(name=name, url=url, icon_url=icon_url)
        return self

    def add_field(self, *, name: str, value: str, inline: bool = True) -> Embed:
        self.fields.append(EmbedField(name=name, value=value, inline=inline))
        return self

    def _to_dict(self, obj: Any):
        return obj.to_dict() if obj is not None else obj

    def to_dict(self) -> Dict[str, Any]:
        payload: dict = {}
        update_payload(
            payload,
            title=self.title,
            description=self.description,
            color=self.color,
            url=self.url,
            timestamp=self.timestamp,
            footer=self._to_dict(self.footer),
            image=self._to_dict(self.image),
            video=self._to_dict(self.video),
            provider=self._to_dict(self.provider),
            author=self._to_dict(self.author),
            fields=[field.to_dict() for field in self.fields],
        )

        return payload

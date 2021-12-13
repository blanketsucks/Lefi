from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Dict, List, Optional, Type, Protocol, Any

from ..utils.payload import update_payload

if TYPE_CHECKING:

    class _EmbedItem(Protocol):
        data: dict

    class EmbedFooter(_EmbedItem):
        text: str
        icon_url: Optional[str]

    class EmbedAuthor(_EmbedItem):
        name: str
        url: Optional[str]
        icon_url: Optional[str]

    class EmbedProvider(_EmbedItem):
        name: Optional[str]
        url: Optional[str]

    class EmbedVideo(_EmbedItem):
        url: str
        height: Optional[int]
        width: Optional[int]

    class EmbedImage(_EmbedItem):
        url: str
        height: Optional[int]
        width: Optional[int]

    class EmbedThumbnail(_EmbedItem):
        url: str
        height: Optional[int]
        width: Optional[int]

    class EmbedField(_EmbedItem):
        name: str
        value: str
        inline: bool


__all__ = ("Embed",)


class EmbedItem:
    def __init__(self, **kwargs: Any) -> None:
        self.data = kwargs
        self.__dict__.update(kwargs)


class Embed:
    """Represents an embed.

    Parameters
    ----------
    title: Optional[:class:`str`]
        The title of the embed

    description: Optional[:class:`str`]
        The description of the embed

    url: Optional[:class:`str`]
        The url of the embed

    timestamp: Optional[:class:`datetime.datetime`]
        The timestamp of the embed

    color: Optional[:class:`int`]
        The color of the embed
    """

    def __init__(self, **kwargs) -> None:
        self._data = kwargs

    @classmethod
    def from_dict(cls: Type[Embed], data: dict) -> Embed:
        """Creates an Embed object from a dict.

        Parameters
        ----------
        data: :class:`dict`
            The data to create the embed from

        Returns
        -------
        :class:`.Embed`
            A created embed from the dict.
        """
        return cls(**data)

    def to_dict(self) -> dict:
        """Creates a dict from the embed.

        Returns
        -------
        :class:`dict`
            The dict created from the embed.
        """
        payload = self._data.copy()

        for name, item in payload.items():
            if isinstance(item, EmbedItem):
                payload[name] = update_payload({}, **item.data)

                continue

            elif isinstance(item, list) and all(isinstance(obj, EmbedItem) for obj in item):
                payload[name] = [update_payload({}, **field.data) for field in item]

        return payload

    @property
    def title(self) -> Optional[str]:
        """The embed's title."""
        return self._data.get("title")

    @title.setter
    def title(self, title: str) -> None:
        """Set the embed's title.

        Characters cannot be more than 256 characters.

        Parameters
        ----------
        title: :class:`str`
            The title to set
        """
        if len(title) > 256:
            raise ValueError("Title cannot have more than 256 characters")

        self._data["title"] = title

    @property
    def description(self) -> Optional[str]:
        """The the embed's description."""
        return self._data.get("description")

    @description.setter
    def description(self, description: str) -> None:
        """Set the embed's description.

        Characters cannot be more than 4096 characters.

        Parameters
        ----------
        description: :class:`str`
            The description to set
        """
        if len(description) > 4096:
            raise ValueError("Description cannot have more than 4096 characters")

        self._data["description"] = description

    @property
    def url(self) -> Optional[str]:
        """The embed's url."""
        return self._data.get("url")

    @url.setter
    def url(self, url: str) -> None:
        """Sets the embed's url.

        Parameters
        ----------
        url: :class:`str`
            The url to set
        """
        self._data["url"] = url

    @property
    def timestamp(self) -> Optional[datetime.datetime]:
        """The embed's timestamp."""
        return self._data.get("timestamp")

    @timestamp.setter
    def timestamp(self, timestamp: datetime.datetime) -> None:
        """Sets the embed's timestamp.

        Parameters
        ----------
        timestamp: :class:`datetime.datetime`
            The datetime.datetime to use as the timestamp
        """
        self._data["timestamp"] = timestamp

    @property
    def color(self) -> Optional[int]:
        """The embed's color."""
        return self._data.get("color")

    @color.setter
    def color(self, color: int) -> None:
        """Sets the embed's color.

        Parameters
        ----------
        color: :class:`int`
            The color to set
        """
        self._data["color"] = color

    @property
    def footer(self) -> Optional[EmbedFooter]:
        """The embed's footer."""
        return self._data.get("footer")

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> None:
        """Sets the embed's footer.

        Parameters
        ----------
        text: :class:`str`
            The text of the footer

        icon_url: Optional[:class:`str`]
            The icon url of the footer
        """
        self._data["footer"] = EmbedItem(text=text, icon_url=icon_url)

    @property
    def image(self) -> Optional[EmbedImage]:
        """The embed's image."""
        return self._data.get("image")

    def set_image(self, url: str, height: Optional[int] = None, width: Optional[int] = None) -> None:
        """Sets the embed's image.

        Parameters
        ----------
        url: :class:`str`
            The url of the image

        height: Optional[:class``int`]
            The height of the image

        width: Optional[:class:`int`]
            The width of the image
        """
        self._data["image"] = EmbedItem(url=url, height=height, width=width)

    @property
    def thumbnail(self) -> Optional[EmbedThumbnail]:
        """The embed's thumbnail."""
        return self._data.get("thumbnail")

    def set_thumbnail(self, url: str, height: Optional[int] = None, width: Optional[int] = None) -> None:
        """Sets the embed's thumbnail.

        Parameters
        ----------
        url: :class:`str`
            The url of the image

        height: Optional[:class:`int`]
            The height of the thumbnail

        width: Optional[:class:`int`]
            The width of the thumbnail
        """
        self._data["thumbnail"] = EmbedItem(url=url, height=height, width=width)

    @property
    def video(self) -> Optional[EmbedVideo]:
        """The embed's video."""
        return self._data.get("video")

    def set_video(self, url: str, height: Optional[int] = None, width: Optional[int] = None) -> None:
        """Sets the embed's video.

        Parameters
        ----------
        url: :class:`str`
            The url of the video

        height: Optional[:class:`int`]
            The height of the video

        width: Optional[:class:`int`]
            The width of the video
        """
        self._data["thumbnail"] = EmbedItem(url=url, height=height, width=width)

    @property
    def provider(self) -> Optional[EmbedProvider]:
        """The embed's provider."""
        return self._data.get("provider")

    def set_provider(self, name: Optional[str] = None, url: Optional[str] = None) -> None:
        """Sets the embed's provider.

        Parameters
        ----------
        name: Optional[:class:`str`]
            The name of the provider

        url: Optional[:class:`str`]
            The url of the provider
        """
        self._data["thumbnail"] = EmbedItem(name=name, url=url)

    @property
    def author(self) -> Optional[EmbedAuthor]:
        """The embed's author."""
        return self._data.get("author")

    def set_author(self, name: str, url: Optional[str] = None, icon_url: Optional[str] = None) -> None:
        """Sets the embed's author.

        Parameters
        ----------
        name: :class:`str`
            The name of the author

        url: Optional[:class:`str`]
            The url of the author

        icon_url: Optional[:class:`str`]
            The icon url of the author
        """
        self._data["author"] = EmbedItem(name=name, url=url, icon_url=icon_url)

    @property
    def fields(self) -> Optional[List[EmbedField]]:
        """The embed's fields."""
        return self._data.get("fields")

    def add_field(self, name: str, value: str, inline: bool = False) -> None:
        """Adds a field to the embed.

        Parameters
        ----------
        name: :class:`str`
            The fields name

        value: :class:`str`
            The value of the field

        inline: :class:`bool`
            Whether or not the field is inline
        """
        self._data.setdefault("fields", []).append(EmbedItem(name=name, value=value, inline=inline))

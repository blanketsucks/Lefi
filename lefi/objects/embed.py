from __future__ import annotations

import datetime

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Generic,
    Optional,
    List,
    Type,
    TypeVar,
    Union,
)
from typing_extensions import TypedDict

from ..utils.payload import update_payload

if TYPE_CHECKING:

    class EmbedFooter(TypedDict):
        text: str
        icon_url: Optional[str]

    class EmbedAuthor(TypedDict):
        name: str
        url: Optional[str]
        icon_url: Optional[str]

    class EmbedProvider(TypedDict):
        name: Optional[str]
        url: Optional[str]

    class EmbedVideo(TypedDict):
        url: str
        height: Optional[int]
        width: Optional[int]

    class EmbedImage(TypedDict):
        url: str
        height: Optional[int]
        width: Optional[int]

    class EmbedThumbnail(TypedDict):
        url: str
        height: Optional[int]
        width: Optional[int]

    class EmbedField(TypedDict):
        name: str
        value: str
        inline: bool


__all__ = ("Embed",)

T = TypeVar("T")


class EmbedItem(Generic[T]):
    def __init__(self, **kwargs: Any) -> None:
        self.data: T = kwargs  # type: ignore
        self.__dict__.update(kwargs)


class Embed:
    """
    Represents a discord embed.

    """

    def __init__(self, **kwargs) -> None:
        """
        Parameters:
            **kwargs: The attributes of the embed

        """
        self._data = kwargs

    @classmethod
    def from_dict(cls: Type[Embed], data: Dict) -> Embed:
        """
        Creates an Embed object from a dictionary.

        Parameters:
            data (Dict): The dictionary to create the embed from.

        Returns:
            The created embed

        """
        return cls(**data)

    def to_dict(self) -> Dict:
        """
        Turns the Embed into a dictionary.

        Returns:
            The created dictionary.

        """
        payload = self._data.copy()

        for name, item in payload.items():
            if isinstance(item, EmbedItem):
                payload[name] = update_payload({}, **item.data)

                continue

            elif isinstance(item, list) and all(
                isinstance(obj, EmbedItem) for obj in item
            ):
                payload[name] = [update_payload({}, **field.data) for field in item]

        return payload

    @property
    def title(self) -> Optional[str]:
        """
        The embed's title.
        """
        return self._data.get("title")

    @title.setter
    def title(self, title: str) -> None:
        """
        Set the embeds title, characters cannot be more than 256 characters.

        Parameters:
            title (str): The new title to use.

        """
        if len(title) > 256:
            raise ValueError("Title cannot have more than 256 characters")

        self._data["title"] = title

    @property
    def description(self) -> Optional[str]:
        """
        The the embed's description.
        """
        return self._data.get("description")

    @description.setter
    def description(self, description: str) -> None:
        """
        Set the embed's description, characters cannot be more than 4096 characters.

        Parameters:
            description (str): The new description to use.

        """
        if len(description) > 4096:
            raise ValueError("Description cannot have more than 4096 characters")

        self._data["description"] = description

    @property
    def url(self) -> Optional[str]:
        """
        The embed's url.
        """
        return self._data.get("url")

    @url.setter
    def url(self, url: str) -> None:
        """
        Sets the embed's url.

        Parameters:
            url (str): The new url to use.

        """
        self._data["url"] = url

    @property
    def timestamp(self) -> Optional[str]:
        """
        The embed's timestamp.
        """
        if timestamp := self._data.get("timestamp"):
            return timestamp.isoformat()

        return None

    @timestamp.setter
    def timestamp(self, timestamp: datetime.datetime) -> None:
        """
        Sets the embed's timestamp.

        Parameters:
            timestamp (datetime.datetime): The datetime.datetime object to use.

        """
        self._data["timestamp"] = timestamp

    @property
    def color(self) -> Optional[int]:
        """
        The embed's color.
        """
        return self._data.get("color")

    @color.setter
    def color(self, color: int) -> None:
        """
        Sets the embed's color.

        Parameters:
            color (int): The new color to use.

        """
        self._data["color"] = color

    @property
    def footer(self) -> Optional[EmbedItem[EmbedFooter]]:
        """
        The embed's footer.
        """
        return self._data.get("footer")

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> None:
        """
        Sets the embed's footer.

        Parameters:
            text (str): The text of the footer.
            icon_url (Optional[str]): The icon url of the footer.

        """
        self._data["footer"] = EmbedItem(text=text, icon_url=icon_url)

    @property
    def image(self) -> Optional[EmbedItem[EmbedImage]]:
        """
        The embed's image.
        """
        return self._data.get("image")

    def set_image(
        self, url: str, height: Optional[int] = None, width: Optional[int] = None
    ) -> None:
        """
        Sets the embed's image.

        Parameters:
            url (str): The url of the image
            height (Optional[int]): The height of the image.
            width (Optional[int]): The width of the image.

        """
        self._data["image"] = EmbedItem(url=url, height=height, width=width)

    @property
    def thumbnail(self) -> Optional[EmbedItem[EmbedThumbnail]]:
        """
        The embed's thumbnail.
        """
        return self._data.get("thumbnail")

    def set_thumbnail(
        self, url: str, height: Optional[int] = None, width: Optional[int] = None
    ) -> None:
        """
        Sets the embed's thumbnail.

        Parameters:
            url (str): The url of the image
            height (Optional[int]): The height of the thumbnail.
            width (Optional[int]): The width of the thumbnail.

        """
        self._data["thumbnail"] = EmbedItem(url=url, height=height, width=width)

    @property
    def video(self) -> Optional[EmbedItem[EmbedVideo]]:
        """
        The embed's video.
        """
        return self._data.get("video")

    def set_video(
        self, url: str, height: Optional[int] = None, width: Optional[int] = None
    ) -> None:
        """
        Sets the embed's video.

        Parameters:
            url (str): The url of the video
            height (Optional[int]): The height of the video.
            width (Optional[int]): The width of the video.

        """
        self._data["thumbnail"] = EmbedItem(url=url, height=height, width=width)

    @property
    def provider(self) -> Optional[EmbedItem[EmbedProvider]]:
        """
        The embed's provider.
        """
        return self._data.get("provider")

    def set_provider(
        self, name: Optional[str] = None, url: Optional[str] = None
    ) -> None:
        """
        Sets the embed's provider.

        Parameters:
            name (Optional[str]): The name of the provider.
            url (Optional[str]): The url of the provider.

        """
        self._data["thumbnail"] = EmbedItem(name=name, url=url)

    @property
    def author(self) -> Optional[EmbedItem[EmbedAuthor]]:
        """
        The embed's author.
        """
        return self._data.get("author")

    def set_author(
        self, name: str, url: Optional[str] = None, icon_url: Optional[str] = None
    ) -> None:
        """
        Sets the embed's author.

        Parameters:
            name (str): The name of the author.
            url (Optional[str]): The url of the author.
            icon_url (Optional[str]): The icon url of the author.

        """
        self._data["author"] = EmbedItem(name=name, url=url, icon_url=icon_url)

    @property
    def fields(self) -> Optional[List[EmbedItem[EmbedField]]]:
        """
        The embed's fields.
        """
        return self._data.get("fields")

    def add_field(self, name: str, value: str, inline: bool = False) -> None:
        """
        Adds a field to the embed.

        Parameters:
            name (str): The fields name.
            value (str): The value of the field.
            inline (bool): Whether or not the field is inline.

        """
        self._data.setdefault("fields", []).append(
            EmbedItem(name=name, value=value, inline=inline)
        )

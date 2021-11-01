from __future__ import annotations

import datetime

from typing import Dict, Optional, List, Type

from ..utils.payload import update_payload

__all__ = ("Embed",)


class EmbedItem:
    def __init__(self, **kwargs) -> None:
        self.data = kwargs


class Embed:
    """
    Represents a discord embed.
    """

    def __init__(self, **kwargs) -> None:
        """
        Parameters:
            **kwargs: The attributes of the embed

        """
        self.data = kwargs

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
        payload = self.data.copy()

        for name, item in self.data.items():
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
        return self.data.get("title")

    @title.setter
    def title(self, title: str) -> None:
        """
        Set the embeds title, characters cannot be more than 256 characters.

        Parameters:
            title (str): The new title to use.

        """
        if len(title) > 256:
            raise ValueError("Title cannot have more than 256 characters")

        self.data["title"] = title

    @property
    def description(self) -> Optional[str]:
        """
        The the embed's description.
        """
        return self.data.get("description")

    @description.setter
    def description(self, description: str) -> None:
        """
        Set the embed's description, characters cannot be more than 4096 characters.

        Parameters:
            description (str): The new description to use.

        """
        if len(description) > 4096:
            raise ValueError("Description cannot have more than 4096 characters")

        self.data["description"] = description

    @property
    def url(self) -> Optional[str]:
        """
        The embed's url.
        """
        return self.data.get("url")

    @url.setter
    def url(self, url: str) -> None:
        """
        Sets the embed's url.

        Parameters:
            url (str): The new url to use.

        """
        self.data["url"] = url

    @property
    def timestamp(self) -> Optional[datetime.datetime]:
        """
        The embed's timestamp.
        """
        if timestamp := self.data.get("timestamp"):
            return timestamp.isoformat()

        return None

    @timestamp.setter
    def timestamp(self, timestamp: datetime.datetime) -> None:
        """
        Sets the embed's timestamp.

        Parameters:
            timestamp (datetime.datetime): The datetime.datetime object to use.

        """
        self.data["timestamp"] = timestamp.isoformat()

    @property
    def color(self) -> Optional[int]:
        """
        The embed's color.
        """
        return self.data.get("color")

    @color.setter
    def color(self, color: int) -> None:
        """
        Sets the embed's color.

        Parameters:
            color (int): The new color to use.

        """
        self.data["color"] = color

    @property
    def footer(self) -> Optional[EmbedItem]:
        """
        The embed's footer.
        """
        return self.data.get("footer")

    def set_footer(self, text: str, icon_url: Optional[str] = None) -> None:
        """
        Sets the embed's footer.

        Parameters:
            text (str): The text of the footer.
            icon_url (Optional[str]): The icon url of the footer.

        """
        self.data["footer"] = EmbedItem(text=text, icon_url=icon_url)

    @property
    def image(self) -> Optional[EmbedItem]:
        """
        The embed's image.
        """
        return self.data.get("image")

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
        self.data["image"] = EmbedItem(url=url, height=height, width=width)

    @property
    def thumbnail(self) -> Optional[EmbedItem]:
        """
        The embed's thumbnail.
        """
        return self.data.get("thumbnail")

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
        self.data["thumbnail"] = EmbedItem(url=url, height=height, width=width)

    @property
    def video(self) -> Optional[EmbedItem]:
        """
        The embed's video.
        """
        return self.data.get("video")

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
        self.data["thumbnail"] = EmbedItem(url=url, height=height, width=width)

    @property
    def provider(self) -> Optional[EmbedItem]:
        """
        The embed's provider.
        """
        return self.data.get("provider")

    def set_provider(
        self, name: Optional[str] = None, url: Optional[str] = None
    ) -> None:
        """
        Sets the embed's provider.

        Parameters:
            name (Optional[str]): The name of the provider.
            url (Optional[str]): The url of the provider.

        """
        self.data["thumbnail"] = EmbedItem(name=name, url=url)

    @property
    def author(self) -> Optional[EmbedItem]:
        """
        The embed's author.
        """
        return self.data.get("author")

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
        self.data["author"] = EmbedItem(name=name, url=url, icon_url=icon_url)

    @property
    def fields(self) -> Optional[List[EmbedItem]]:
        """
        The embed's fields.
        """
        return self.data.get("fields")

    def add_field(self, name: str, value: str, inline: bool = False) -> None:
        """
        Adds a field to the embed.

        Parameters:
            name (str): The fields name.
            value (str): The value of the field.
            inline (bool): Whether or not the field is inline.

        """
        self.data.setdefault("fields", []).append(
            EmbedItem(name=name, value=value, inline=inline)
        )

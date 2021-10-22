from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional

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
    """
    Represents an Embed's footer.

    Attributes:
        text (str): The content of the footer.
        icon_url (str): The icon url of the footer.

    """

    def __init__(self, *, text: str, icon_url: Optional[str] = None) -> None:
        """
        Parameters:
            text (str): The text for the footer.
            icon_url (Optional[str]): The icon url for the footer.

        """
        self.text = text
        self.icon_url = icon_url

    def to_dict(self) -> Dict[str, Any]:
        """
        Turns the footer into a raw dict.

        Returns:
            The dict representing the footer.

        """
        payload = {"text": self.text}
        update_payload(payload, icon_url=self.icon_url)

        return payload


class EmbedImage:
    """
    Represents an Embed's image.

    Attributes:
        url (str): The image's url.
        height (Optional[int]): The height of the image.
        width (Optional[int]): The width of the image.

    """

    def __init__(
        self, *, url: str, height: Optional[int] = None, width: Optional[int] = None
    ) -> None:
        self.url = url
        self.height = height
        self.width = width

    def to_dict(self) -> Dict[str, Any]:
        """
        Turns the image into a raw dict.

        Returns:
            The dict representing the image.

        """
        payload = {"url": self.url}
        update_payload(payload, height=self.height, width=self.width)

        return payload


class EmbedVideo(EmbedImage):
    """
    Represents a Embed's video.

    Attributes:
        url (str): The videos url.
        height (Optional[int]): The height of the video.
        width (Optional[int]): The width of the video.

    """

    def __init__(
        self, *, url: str, height: Optional[int] = None, width: Optional[int] = None
    ) -> None:
        """
        Parameters:
            url (str): The url of the video.
            height (Optional[int]): The height of the video.
            width (Optional[int]): The width of the video.

        """

        super().__init__(url=url, height=height, width=width)

    def to_dict(self) -> Dict[str, Any]:
        """
        Turns the image into a raw dict.

        Returns:
            The dict representing the video.

        """
        return update_payload({}, **super().to_dict())


class EmbedProvider:
    """
    Representing an Embed's provider.

    Attributes:
        name (str): The name of the provider.
        url (str): The url of the provider.

    """

    def __init__(
        self, *, name: Optional[str] = None, url: Optional[str] = None
    ) -> None:
        """
        Parameters:
            name (str): The name of the provider.
            url (str): The url of the provider.

        """
        self.name = name
        self.url = url

    def to_dict(self) -> Dict[str, Any]:
        """
        Turns the provider into a raw dict.

        Returns:
            The dict representing the provider.

        """
        return update_payload({}, name=self.name, url=self.url)


class EmbedAuthor:
    """
    Represents an Embed's author.

    Attributes:
        name (str): The name of the author.
        url (str): The url of the author.
        icon_url (str): The icon url of the author.

    """

    def __init__(
        self, *, name: str, url: Optional[str] = None, icon_url: Optional[str] = None
    ) -> None:
        """
        Parameters:
            name (str): The name of the author.
            url (Optional[str]): The url of the author.
            icon_url (Optional[str]): The icon url of the author.

        """
        self.name = name
        self.url = url
        self.icon_url = icon_url

    def to_dict(self) -> Dict[str, Any]:
        """
        Turns the author to a raw dict.

        Returns:
            The dict representing the author.

        """
        return update_payload({}, name=self.name, url=self.url, icon_url=self.icon_url)


class EmbedField:
    """
    Represents an Embed's field.

    Attributes:
        name (str): The name of the field.
        value (str): The value of the field.
        inline (bool): Whether the field is inline or not.

    """

    def __init__(self, *, name: str, value: str, inline: bool = True) -> None:
        """
        Parameters:
            name (str): The name of the field.
            value (str): The value of the field.
            inline (bool): Whether the field is inline or not.

        """
        self.name = name
        self.value = value
        self.inline = inline

    def to_dict(self) -> Dict[str, Any]:
        """
        Turns the field into a raw dict.

        Returns:
            The dict representing the field.

        """
        return update_payload({}, name=self.name, value=self.value, inline=self.inline)


class Embed:
    """
    Represents an Embed.

    Attributes:
        title (Optional[str]): The title of the embed.
        description (Optional[str]): The description of the embed.
        color (Optional[int]): The color of the embed.
        url (Optional[str]): The url of the embed.
        timestamp (Optional[datetime.datetime]): The timestamp of the embed.
        footer (Optional[lefi.EmbedFooter]): The footer of the embed.
        image (Optional[lefi.EmbedImage]): The image of the embed.
        video (Optional[lefi.EmbedVideo]): The video of the embed.
        provider (Optional[lefi.EmbedProvider]): The provider of the embed.
        author (Optional[lefi.EmbedAuthor]): The author of the embed.
        fields (Optional[List[lefi.EmbedField]]): The list of fields for the embed.

    Note:
        You shouldn't be creating all the classes to pass in.
        Rather use the `set_` methods of [lefi.Embed][]

    """

    def __init__(
        self,
        *,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[int] = None,
        url: Optional[str] = None,
        timestamp: Optional[datetime.datetime] = None,
        footer: Optional[EmbedFooter] = None,
        image: Optional[EmbedImage] = None,
        video: Optional[EmbedVideo] = None,
        provider: Optional[EmbedProvider] = None,
        author: Optional[EmbedAuthor] = None,
        fields: Optional[List[EmbedField]] = None
    ) -> None:
        """
        Parameters:
            title (Optional[str]): The title of the embed.
            description (Optional[str]): The description of the embed.
            color (Optional[int]): The color of the embed.
            url (Optional[str]): The url of the embed.
            timestamp (Optional[datetime.datetime]): The timestamp of the embed.
            footer (Optional[lefi.EmbedFooter]): The footer of the embed.
            image (Optional[lefi.EmbedImage]): The image of the embed.
            video (Optional[lefi.EmbedVideo]): The video of the embed.
            provider (Optional[lefi.EmbedProvider]): The provider of the embed.
            author (Optional[lefi.EmbedAuthor]): The author of the embed.
            fields (Optional[List[lefi.EmbedField]]): The list of fields for the embed.

        """
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

    def set_footer(self, *, text: str, icon_url: Optional[str] = None) -> Embed:
        """
        Sets the footer of the embed.

        Parameters:
            text (str): The text of the footer.
            icon_url (str): The icon url of the footer

        """
        self.footer = EmbedFooter(text=text, icon_url=icon_url)
        return self

    def set_image(
        self, *, url: str, height: Optional[int] = None, width: Optional[int] = None
    ) -> Embed:
        """
        Sets the image of the embed.

        Parameters:
            url (str): The images url.
            height (Optional[int]): The height of the image.
            width (Optional[int]): The width of the image.

        """
        self.image = EmbedImage(url=url, height=height, width=width)
        return self

    def set_video(
        self, *, url: str, height: Optional[int] = None, width: Optional[int] = None
    ) -> Embed:
        """
        Sets the video of the embed.

        Parameters:
            url (str): The video url.
            height (Optional[int]): The height of the video.
            width (Optional[int]): The width of the video.

        """
        self.video = EmbedVideo(url=url, height=height, width=width)
        return self

    def set_provider(
        self, *, name: Optional[str] = None, url: Optional[str] = None
    ) -> Embed:
        """
        Sets the provider of the embed.

        Parameters:
            name (Optional[str]): The name of the provider.
            url (Optional[str]): The url of the provider.

        """
        self.provider = EmbedProvider(name=name, url=url)
        return self

    def set_author(
        self, *, name: str, url: Optional[str] = None, icon_url: Optional[str] = None
    ) -> Embed:
        """
        Sets the author of the embed.

        Parameters:
            name (str): The name of the author.
            url (Optional[str]): The url of the author.
            icon_url (Optional[str]): The icon url of the author.

        """
        self.author = EmbedAuthor(name=name, url=url, icon_url=icon_url)
        return self

    def add_field(self, *, name: str, value: str, inline: bool = True) -> Embed:
        """
        Adds a field to the embed.

        Parameters:
            name (str): The name of the field.
            value (str): The vaue of the field.
            inline (bool): Whether the field is inline or not.

        """
        self.fields.append(EmbedField(name=name, value=value, inline=inline))
        return self

    def _to_dict(self, obj: Any):
        return obj.to_dict() if obj is not None else obj

    def to_dict(self) -> Dict[str, Any]:
        """
        Turns the embed into a raw dict.

        Returns:
            The dict representing the embed.

        """
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

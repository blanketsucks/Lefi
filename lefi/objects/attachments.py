from __future__ import annotations

from typing import TYPE_CHECKING, BinaryIO, ClassVar, Optional, Tuple, Union, Type
import io
import os
import asyncio

from .files import File

if TYPE_CHECKING:
    from ..state import State

__all__ = (
    "Attachment",
    "CDNAsset",
)


def _sync_save(fp: str, data: bytes) -> None:
    with open(fp, "wb") as f:
        _sync_write(f, data)


def _sync_write(fp: BinaryIO, data: bytes) -> None:
    fp.write(data)


def is_animated(hash: str) -> Tuple[bool, str]:
    animated = hash.startswith("a_")
    format = "gif" if animated else "png"

    return animated, format


class AttachmentMixin:
    """A mixin class for attachments."""

    async def read(self) -> bytes:
        """Gets the bytes of the attachment.

        Returns
        -------
        :class:`bytes`
            The bytes of the attachment.
        """
        return await self._state.http.read_from_url(self.url)  # type: ignore

    async def save(self, file: Union[BinaryIO, os.PathLike[str]]) -> None:
        """Saves the attachment to a file.

        Parameters
        ----------
        file: Union[:class:`typing.BinaryIO`, :class:`os.PathLike`]
            The file to save the data to
        """
        data = await self.read()

        if isinstance(file, (str, os.PathLike)):
            await asyncio.to_thread(_sync_save, file, data)
        else:
            await asyncio.to_thread(_sync_write, file, data)


class Attachment(AttachmentMixin):
    """A class used to represent attachments."""

    def __init__(self, state: State, data: dict) -> None:
        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f"<Attachment id={self.id} filename={self.filename!r} url={self.url!r} size={self.size}>"

    def __str__(self) -> str:
        return self.url

    @property
    def filename(self) -> str:
        """The name of the file."""
        return self._data["filename"]

    @property
    def id(self) -> int:
        """The id of the attachment."""
        return int(self._data["id"])

    @property
    def description(self) -> Optional[str]:
        """The description of the attachment."""
        return self._data.get("description")

    @property
    def content_type(self) -> Optional[str]:
        """The content type of the attachment."""
        return self._data.get("content_type")

    @property
    def size(self) -> int:
        """The size of the attacment."""
        return self._data["size"]

    @property
    def url(self) -> str:
        """The url of the attachment."""
        return self._data["url"]

    @property
    def proxy_url(self) -> str:
        """The proxied url of the attachment."""
        return self._data["proxy_url"]

    @property
    def height(self) -> Optional[int]:
        """The height of the attachment."""
        return self._data.get("height")

    @property
    def width(self) -> Optional[int]:
        """The width of the attachment."""
        return self._data.get("width")

    @property
    def ephemeral(self) -> bool:
        """Whether or not this attachment is ephemeral."""
        return self._data.get("ephemeral", False)

    def is_spoiler(self) -> bool:
        """Checks if an attachment is a spoiler.

        Returns
        -------
        :class:`bool`
            If the attachment is a spoiler or not.
        """
        return self.filename.startswith("SPOILER_")

    def to_dict(self) -> dict:
        """Creates a dict from the attachment.

        Returns
        -------
        :class:`dict`
            The dict representing the attachment.
        """
        return {
            "id": self.id,
            "description": self.description,
            "filename": self.filename,
        }

    async def to_file(self) -> File:
        """Turns the attachment into a :class:`.File`

        Returns
        -------
        :class:`.File`
            The newly constructed file representing the attachment.
        """
        data = io.BytesIO(await self.read())
        file = File(data, filename=self.filename)

        return file


class CDNAsset(AttachmentMixin):
    """This class represents a CDN asset.

    Attributes
    ----------
    url: :class:`str`
        The url of the CDN asset

    animated: :class:`bool`
        Whether or not the CDN asset is animated

    hash: :class:`str`
        The hash of the CDN asset
    """

    BASE: ClassVar[str] = "https://cdn.discordapp.com/"

    def __init__(self, state: State, path: str, animated: bool, hash: str) -> None:
        self._state = state

        self.url = self.BASE + path
        self.animated = animated
        self.hash = hash

    def __repr__(self) -> str:
        return f"<CDNAsset animated={self.animated} url={self.url!r}>"

    def __str__(self) -> str:
        return self.url

    @classmethod
    def from_emoji(cls: Type[CDNAsset], state: State, emoji_id: int) -> CDNAsset:
        path = f"emojis/{emoji_id}.png"
        return cls(state, path, False, str(emoji_id))

    @classmethod
    def from_guild_icon(cls, state: State, guild_id: int, icon_hash: str) -> CDNAsset:
        animated, format = is_animated(icon_hash)

        path = f"icons/{guild_id}/{icon_hash}.{format}"
        return cls(state, path, animated, icon_hash)

    @classmethod
    def from_guild_splash(
        cls, state: State, guild_id: int, splash_hash: str
    ) -> CDNAsset:
        path = f"splashes/{guild_id}/{splash_hash}.png"
        return cls(state, path, False, splash_hash)

    @classmethod
    def from_guild_discovery_splash(
        cls, state: State, guild_id: int, discovery_hash: str
    ):
        path = f"discovery-splashes/{guild_id}/{discovery_hash}.png"
        return cls(state, path, False, discovery_hash)

    @classmethod
    def from_guild_banner(
        cls, state: State, guild_id: int, banner_hash: str
    ) -> CDNAsset:
        path = f"banners/{guild_id}/{banner_hash}.png"
        return cls(state, path, False, banner_hash)

    @classmethod
    def from_user_banner(cls, state: State, user_id: int, banner_hash: str) -> CDNAsset:
        animated, format = is_animated(banner_hash)

        path = f"banners/{user_id}/{banner_hash}.{format}"
        return cls(state, path, animated, banner_hash)

    @classmethod
    def from_default_user_avatar(cls, state: State, discriminator: int) -> CDNAsset:
        path = f"embed/avatars/{discriminator}.png"
        return cls(state, path, False, str(discriminator))

    @classmethod
    def from_user_avatar(cls, state: State, user_id: int, avatar_hash: str) -> CDNAsset:
        animated, format = is_animated(avatar_hash)

        path = f"avatars/{user_id}/{avatar_hash}.{format}"
        return cls(state, path, animated, avatar_hash)

    @classmethod
    def from_guild_member_avatar(
        cls, state: State, guild_id: int, user_id: int, avatar_hash: str
    ) -> CDNAsset:
        animated, format = is_animated(avatar_hash)

        path = f"guilds/{guild_id}/users/{user_id}/avatars/{avatar_hash}.{format}"
        return cls(state, path, animated, avatar_hash)

    @classmethod
    def from_application_icon(
        cls, state: State, application_id: int, icon_hash: str
    ) -> CDNAsset:
        path = f"app-icons/{application_id}/{icon_hash}.png"
        return cls(state, path, False, icon_hash)

    @classmethod
    def from_application_cover(
        cls, state: State, application_id: int, cover_hash: str
    ) -> CDNAsset:
        path = f"app-icons/{application_id}/{cover_hash}.png"
        return cls(state, path, False, cover_hash)

    @classmethod
    def from_application_asset(
        cls, state: State, application_id: int, asset_hash: str
    ) -> CDNAsset:
        path = f"app-assets/{application_id}/{asset_hash}.png"
        return cls(state, path, False, asset_hash)

    @classmethod
    def from_achievement_icon(
        cls, state: State, achievement_id: int, icon_hash: str
    ) -> CDNAsset:
        path = f"achievements/{achievement_id}/{icon_hash}.png"
        return cls(state, path, False, icon_hash)

    @classmethod
    def from_sticker_pack_banner(cls, state: State, pack_id: int) -> CDNAsset:
        path = f"app-assets/710982414301790216/store/{pack_id}.png"
        return cls(state, path, False, str(pack_id))

    @classmethod
    def from_team_icon(cls, state: State, team_id: int, icon_hash: str) -> CDNAsset:
        path = f"teams/{team_id}/{icon_hash}.png"
        return cls(state, path, False, icon_hash)

    @classmethod
    def from_sticker(cls, state: State, sticker_id: int) -> CDNAsset:
        path = f"stickers/{sticker_id}.png"
        return cls(state, path, False, str(sticker_id))

    @classmethod
    def from_role_icon(cls, state: State, role_id: int, icon_hash: str) -> CDNAsset:
        path = f"role-iconss/{role_id}/{icon_hash}.png"
        return cls(state, path, False, icon_hash)

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional
from functools import cached_property

from .enums import StickerFormatType, StickerType
from ..utils import to_snowflake
from .user import User
from .attachments import CDNAsset

if TYPE_CHECKING:
    from ..state import State
    from .guild import Guild


class Sticker:
    def __init__(self, state: State, data: Dict):
        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f"<Sticker id={self.id} name={self.name!r}>"

    @property
    def id(self) -> int:
        return int(self._data["id"])

    @property
    def pack_id(self) -> Optional[int]:
        return to_snowflake(self._data, "pack_id")

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def description(self) -> Optional[str]:
        return self._data["description"]

    @property
    def tags(self) -> List[str]:
        tags = self._data["tags"]
        return tags.split(", ")

    @property
    def type(self) -> StickerType:
        return StickerType(self._data["type"])

    @property
    def format_type(self) -> StickerFormatType:
        return StickerFormatType(self._data["format_type"])

    @property
    def available(self) -> bool:
        return self._data.get("available", False)

    @property
    def guild_id(self) -> Optional[int]:
        return to_snowflake(self._data, "guild_id")

    @property
    def guild(self) -> Optional[Guild]:
        return self._state.get_guild(self.guild_id)  # type: ignore

    @property
    def user(self) -> Optional[User]:
        user = self._data.get("user")
        if user:
            return User(self._state, user)

        return None

    @property
    def asset(self) -> CDNAsset:
        return CDNAsset.from_sticker(self._state, self.id)

    async def delete(self) -> None:
        if not self.guild_id:
            return None

        await self._state.http.delete_guild_sticker(
            guild_id=self.guild_id, sticker_id=self.id
        )

        return None

    async def edit(
        self,
        *,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> None:
        if not self.guild_id:
            return

        if tags is not None:
            tags = ", ".join(tags)  # type: ignore

        await self._state.http.modify_guild_sticker(
            guild_id=self.guild_id,
            sticker_id=self.id,
            name=name,
            tags=tags,  # type: ignore
            description=description,
        )


class StickerPack:
    def __init__(self, state: State, data: Dict):
        self._state = state
        self._data = data

    def __repr__(self) -> str:
        return f"<StickerPack id={self.id} name={self.name!r}>"

    @property
    def id(self) -> int:
        return int(self._data["id"])

    @property
    def cover_sticker_id(self) -> Optional[int]:
        return to_snowflake(self._data, "cover_sticker_id")

    @property
    def banner_asset_id(self) -> int:
        return int(self._data["banner_asset_id"])

    @property
    def banner(self) -> CDNAsset:
        return CDNAsset.from_sticker_pack_banner(self._state, self.banner_asset_id)

    @property
    def name(self) -> str:
        return self._data["name"]

    @property
    def description(self) -> str:
        return self._data["description"]

    @cached_property
    def stickers(self) -> List[Sticker]:
        return [Sticker(self._state, sticker) for sticker in self._data["stickers"]]

    @property
    def sku_id(self) -> int:
        return int(self._data["sku_id"])

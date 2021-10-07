from __future__ import annotations

import aiohttp
import asyncio

from typing import ClassVar, List, Dict, Any

from .utils import MISSING, update_payload
from .errors import HTTPException, Forbidden, NotFound, BadRequest, Unauthorized

__all__ = ("HTTPClient",)

BASE: str = "https://discord.com/api/v9"


class HTTPClient:
    ERRORS: ClassVar[Dict[int, Any]] = {
        400: BadRequest,
        401: Unauthorized,
        403: Forbidden,
        404: NotFound,
    }

    def __init__(self, token: str, loop: asyncio.AbstractEventLoop) -> None:
        self.token: str = token
        self.loop: asyncio.AbstractEventLoop = loop
        self.session: aiohttp.ClientSession = MISSING

    async def _create_session(
        self, loop: asyncio.AbstractEventLoop = MISSING
    ) -> aiohttp.ClientSession:
        return aiohttp.ClientSession(
            loop=self.loop or loop, headers={"Authorization": f"Bot {self.token}"}
        )

    async def request(self, method: str, path: str, **kwargs) -> Any:
        if self.session is MISSING or self.session.closed:
            self.session = await self._create_session()

        url = BASE + path

        async with self.session.request(method, url, **kwargs) as resp:
            try:
                data = await resp.json()
            except aiohttp.ContentTypeError:
                data = await resp.text()

            if resp.status in (200, 201, 204, 304):
                return data

            if resp.status == 429:
                retry_after = float(data["retry_after"])  # type: ignore
                await asyncio.sleep(retry_after)

                return await self.request(method=method, path=path, **kwargs)

            error = self.ERRORS.get(resp.status, HTTPException)
            raise error(data)

    async def get_bot_gateway(self) -> Dict:
        return await self.request("GET", "/gateway/bot")

    async def ws_connect(self, url: str) -> aiohttp.ClientWebSocketResponse:
        return await self.session.ws_connect(url)

    async def login(self) -> None:
        try:
            await self.request("GET", "/users/@me")
        except (Forbidden, Unauthorized):
            raise ValueError("Invalid token")

    async def get_channel(self, channel_id: int) -> Dict[str, Any]:
        return await self.request("GET", f"/channels/{channel_id}")

    async def edit_text_channel(
        self,
        channel_id: int,
        *,
        name: str = MISSING,
        type: int = MISSING,
        position: int = MISSING,
        topic: str = MISSING,
        nsfw: bool = MISSING,
        rate_limit_per_user: int = MISSING,
        permission_overwrites: List[Dict[str, Any]] = MISSING,
        parent_id: int = MISSING,
        default_auto_archive_duration: int = MISSING,
    ) -> Dict[str, Any]:
        payload = update_payload(
            {},
            name=name,
            type=type,
            position=position,
            topic=topic,
            nsfw=nsfw,
            rate_limit_per_user=rate_limit_per_user,
            permission_overwrites=permission_overwrites,
            parent_id=parent_id,
            default_auto_archive_duration=default_auto_archive_duration,
        )

        return await self.request("PATCH", f"/channels/{channel_id}", json=payload)

    async def edit_voice_channel(
        self,
        channel_id: int,
        *,
        name: str = MISSING,
        position: int = MISSING,
        bitrate: int = MISSING,
        user_limit: int = MISSING,
        rtc_region: str = MISSING,
        video_quality_mode: int = MISSING,
    ) -> Dict[str, Any]:
        payload = update_payload(
            {},
            name=name,
            position=position,
            bitrate=bitrate,
            user_limit=user_limit,
            rtc_region=rtc_region,
            video_quality_mode=video_quality_mode,
        )

        return await self.request("PATCH", f"/channels/{channel_id}", json=payload)

    async def get_channel_messages(
        self,
        channel_id: int,
        *,
        around: int = MISSING,
        before: int = MISSING,
        after: int = MISSING,
        limit: int = 50,
    ) -> Dict[str, Any]:
        params = {"limit": limit}

        update_payload(params, around=around, before=before, after=after)

        return await self.request(
            "GET", f"/channels/{channel_id}/messages", params=params
        )

    async def get_channel_message(
        self, channel_id: int, message_id: int
    ) -> Dict[str, Any]:
        return await self.request(
            "GET", f"/channels/{channel_id}/messages/{message_id}"
        )

    async def send_message(
        self,
        channel_id: int,
        content: str = MISSING,
        *,
        tts: bool = False,
        embeds: List[Dict[str, Any]] = MISSING,
        allowed_mentions: Dict[str, Any] = MISSING,
        message_reference: Dict[str, Any] = MISSING,
        components: List[Dict[str, Any]] = MISSING,
        sticker_ids: List[int] = MISSING,
    ) -> Dict[str, Any]:
        payload = {"tts": tts}

        update_payload(
            payload,
            content=content,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            message_reference=message_reference,
            components=components,
            sticker_ids=sticker_ids,
        )

        return await self.request(
            "POST", f"/channels/{channel_id}/messages", json=payload
        )

    async def crosspost_message(
        self, channel_id: int, message_id: int
    ) -> Dict[str, Any]:
        return await self.request(
            "POST", f"/channels/{channel_id}/messages/{message_id}/crosspost"
        )

    async def create_reaction(self, channel_id: int, message_id: int, emoji: str):
        return await self.request(
            method="PUT",
            path=f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me",
        )

    async def delete_reaction(
        self, channel_id: int, message_id: int, emoji: str, user_id: int = MISSING
    ) -> None:
        if user_id is not MISSING:
            path = f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/{user_id}"
        else:
            path = f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me"

        await self.request("DELETE", path)

    async def get_reactions(
        self,
        channel_id: int,
        message_id: int,
        emoji: str,
        *,
        after: int = MISSING,
        limit: int = 25,
    ) -> Dict[str, Any]:
        params = {"limit": limit}

        update_payload(params, after=after)
        return await self.request(
            method="GET",
            path=f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}",
            params=params,
        )

    async def delete_all_reactions(self, channel_id: int, message_id: int, emoji: str):
        return await self.request(
            "DELETE", f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}"
        )

    async def edit_message(
        self,
        channel_id: int,
        message_id: int,
        *,
        content: str = MISSING,
        embeds: List[Dict[str, Any]] = MISSING,
        flags: int = MISSING,
        allowed_mentions: Dict[str, Any] = MISSING,
        attachments: List[Dict[str, Any]] = MISSING,
        components: List[Dict[str, Any]] = MISSING,
    ) -> Dict[str, Any]:
        payload: dict = {}
        update_payload(
            payload,
            content=content,
            embeds=embeds,
            flags=flags,
            allowed_mentions=allowed_mentions,
            attachments=attachments,
            components=components,
        )

        return await self.request(
            method="PATCH",
            path=f"/channels/{channel_id}/messages/{message_id}",
        )

    async def delete_message(self, channel_id: int, message_id: int):
        return await self.request(
            "DELETE", f"/channels/{channel_id}/messages/{message_id}"
        )

    async def bulk_delete_messages(self, channel_id: int, message_ids: List[int]):
        payload = {"messages": message_ids}
        return await self.request(
            "POST", f"/channels/{channel_id}/messages/bulk-delete", json=payload
        )

    async def edit_channel_permissions(
        self,
        channel_id: int,
        overwrite_id: int,
        *,
        allow: int = MISSING,
        deny: int = MISSING,
        type: str = MISSING,
    ):
        payload: dict = {}
        update_payload(payload, allow=allow, deny=deny, type=type)

        return await self.request(
            method="PUT",
            path=f"/channels/{channel_id}/permissions/{overwrite_id}",
            json=payload,
        )

    async def delete_channel_permissions(self, channel_id: int, overwrite_id: int):
        return await self.request(
            "DELETE", f"/channels/{channel_id}/permissions/{overwrite_id}"
        )

    async def get_channel_invites(self, channel_id: int):
        return await self.request("GET", f"/channels/{channel_id}/invites")

    async def create_channel_invite(
        self,
        channel_id: int,
        *,
        max_age: int = 86400,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = False,
        target_type: int = MISSING,
        target_user_id: int = MISSING,
        target_application_id: int = MISSING,
    ):
        payload = {
            "max_age": max_age,
            "max_uses": max_uses,
            "temporary": temporary,
            "unique": unique,
        }
        update_payload(
            payload,
            target_type=target_type,
            target_user_id=target_user_id,
            target_application_id=target_application_id,
        )

        return await self.request(
            "POST", f"/channels/{channel_id}/invites", json=payload
        )

    async def follow_news_channel(self, channel_id: int, webhook_channel_id: int):
        payload = {"webhook_channel_id": webhook_channel_id}
        return await self.request(
            "PUT", f"/channels/{channel_id}/followers/@me", json=payload
        )

    async def trigger_typing(self, channel_id: int):
        return await self.request("POST", f"/channels/{channel_id}/typing")

    async def get_pinned_messages(self, channel_id: int):
        return await self.request("GET", f"/channels/{channel_id}/pins")

    async def pin_message(self, channel_id: int, message_id: int):
        return await self.request("PUT", f"/channels/{channel_id}/pins/{message_id}")

    async def unpin_message(self, channel_id: int, message_id: int):
        return await self.request("DELETE", f"/channels/{channel_id}/pins/{message_id}")

    async def start_thread_with_message(
        self, channel_id: int, message_id: int, *, name: str, auto_archive_duration: int
    ):
        payload = {"name": name, "auto_archive_duration": auto_archive_duration}
        return await self.request(
            method="POST",
            path=f"/channels/{channel_id}/messages/{message_id}/threads",
            json=payload,
        )

    async def start_thread_without_message(
        self,
        channel_id: int,
        *,
        name: str,
        auto_archive_duration: int,
        type: int = MISSING,
        invitable: bool = MISSING,
    ):
        payload = {"name": name, "auto_archive_duration": auto_archive_duration}
        update_payload(payload, type=type, invitable=invitable)

        return await self.request(
            method="POST", path=f"/channels/{channel_id}/threads", json=payload
        )

    async def join_thread(self, channel_id: int):
        return await self.request("PUT", f"/channels/{channel_id}/thread-members/@me")

    async def add_thread_member(self, channel_id: int, user_id: int):
        return await self.request(
            "PUT", f"/channels/{channel_id}/thread-members/{user_id}"
        )

    async def leave_thread(self, channel_id: int):
        return await self.request(
            "DELETE", f"/channels/{channel_id}/thread-members/@me"
        )

    async def remove_thread_member(self, channel_id: int, user_id: int):
        return await self.request(
            "DELETE", f"/channels/{channel_id}/thread-members/{user_id}"
        )

    async def list_thread_members(self, channel_id: int):
        return await self.request("GET", f"/channels/{channel_id}/thread-members")

    async def list_active_threads(self, channel_id: int):
        return await self.request("GET", f"/channels/{channel_id}/threads/active")

    async def list_public_archived_threads(
        self, channel_id: int, *, before: int = MISSING, limit: int = MISSING
    ):
        params = update_payload({}, before=before, limit=limit)
        return await self.request(
            "GET", f"/channels/{channel_id}/threads/archived/public", params=params
        )

    async def list_private_archived_threads(
        self, channel_id: int, *, before: int = MISSING, limit: int = MISSING
    ):
        params = update_payload({}, before=before, limit=limit)
        return await self.request(
            "GET", f"/channels/{channel_id}/threads/archived/private", params=params
        )

    async def list_joined_private_archived_threads(
        self, channel_id: int, *, before: int = MISSING, limit: int = MISSING
    ):
        params = update_payload({}, before=before, limit=limit)
        return await self.request(
            "GET",
            f"/channels/{channel_id}/users/@me/threads/archived/private",
            params=params,
        )

    async def list_guild_emojis(self, guild_id: int):
        return await self.request("GET", f"/guilds/{guild_id}/emojis")

    async def get_guild_emoji(self, guild_id: int, emoji_id: int):
        return await self.request("GET", f"/guilds/{guild_id}/emojis/{emoji_id}")

    async def create_guild_emoji(
        self,
        guild_id: int,
        *,
        name: str,
        image: str,
        roles: List[int] = MISSING,
    ) -> dict:
        payload = {
            "name": name,
            "image": image,
            "roles": [] if roles is MISSING else roles,
        }

        return await self.request(
            method="POST", path=f"/guilds/{guild_id}/emojis", json=payload
        )

    async def modify_guild_emoji(
        self, guild_id: int, emoji_id: int, *, name: str, roles: List[int] = MISSING
    ) -> dict:
        payload = {
            "name": name,
        }
        update_payload(payload, roles=roles)

        return await self.request(
            method="PATCH", path=f"/guilds/{guild_id}/emojis/{emoji_id}", json=payload
        )

    async def delete_guild_emoji(self, guild_id: int, emoji_id: int):
        return await self.request("DELETE", f"/guilds/{guild_id}/emojis/{emoji_id}")

    async def create_dm_channel(self, recipient_id: int) -> Dict[str, Any]:
        payload = {"recipient_id": recipient_id}
        return await self.request("POST", "/users/@me/channels", json=payload)

    async def modifiy_guild_role(
        self,
        guild_id: int,
        role_id: int,
        *,
        name: str = MISSING,
        permissions: int = MISSING,
        color: int = MISSING,
        hoist: bool = MISSING,
        mentionable: bool = MISSING,
    ) -> Dict[str, Any]:
        payload = update_payload(
            {},
            name=name,
            permissions=permissions,
            color=color,
            hoist=hoist,
            mentionable=mentionable,
        )

        return await self.request(
            method="PATCH", path=f"/guilds/{guild_id}/roles/{role_id}", json=payload
        )

    async def delete_guild_role(self, guild_id: int, role_id: int):
        return await self.request("DELETE", f"/guilds/{guild_id}/roles/{role_id}")

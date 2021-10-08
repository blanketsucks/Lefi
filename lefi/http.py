from __future__ import annotations

import aiohttp
import asyncio

from typing import ClassVar, List, Dict, Any, Optional

from .utils import update_payload
from .errors import HTTPException, Forbidden, NotFound, BadRequest, Unauthorized

__all__ = ("HTTPClient",)

BASE: str = "https://discord.com/api/v9"


class HTTPClient:
    """
    A class used to send and handle requests to the discord API.

    Attributes:
        token (str): The clients token, used for authorization.
        loop (asyncio.AbstractEventLoop): The [asyncio.AbstractEventLoop][] being used.
        session (aiohttp.ClientSession): The [aiohttp.ClientSession][] to use for sending requests.

    Note:
        This class is used behind the scenes, this is not intended to be called directly.

    """

    ERRORS: ClassVar[Dict[int, Any]] = {
        400: BadRequest,
        401: Unauthorized,
        403: Forbidden,
        404: NotFound,
    }

    def __init__(self, token: str, loop: asyncio.AbstractEventLoop) -> None:
        """
        Parameters:
            token (str): The token to use for authorzation.
            loop (asyncio.AbstractEventLoop): The [asyncio.AbstractEventLoop][] to use.
            session (aiohttp.ClientSession): The [aiohttp.ClientSession][] to use for sending requests.

        """
        self.token: str = token
        self.loop: asyncio.AbstractEventLoop = loop
        self.session: aiohttp.ClientSession = None  # type: ignore

    async def _create_session(self, loop: asyncio.AbstractEventLoop = None) -> aiohttp.ClientSession:
        """
        Creates the session to use if one wasn't given during construction.

        Parameters:
            loop (asyncio.AbstractEventLoop): The [asyncio.AbstractEventLoop][] to use for the session.

        Returns:
            The created [aiohttp.ClientSession][] instance.

        """
        return aiohttp.ClientSession(loop=self.loop or loop, headers={"Authorization": f"Bot {self.token}"})

    async def request(self, method: str, path: str, **kwargs) -> Any:
        """
        Makes a request to the discord API.

        Parameters:
            method (str): The method for the request.
            path (str): The endpoint which to send the request to.
            **kwargs (Any): Any extra options to pass to [aiohttp.ClientSession.request][]

        Returns:
            The data returned from the request.

        Raises:
            [lefi.errors.HTTPException][] if any error was received from the request.

        """

        if self.session is None or self.session.closed:
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
        """
        A method which gets the gateway url.

        Returns:
            A dict which should contain the url.

        """
        return await self.request("GET", "/gateway/bot")

    async def ws_connect(self, url: str) -> aiohttp.ClientWebSocketResponse:
        """
        A method which attempts to connect to the websocket.

        Returns:
            A [aiohttp.ClientWebSocketResponse][] instance.

        """
        return await self.session.ws_connect(url)

    async def login(self) -> None:
        """
        Checks to see if the token given is valid.

        Raises:
            ValueError if an invalid token was passed.

        """
        try:
            await self.request("GET", "/users/@me")
        except (Forbidden, Unauthorized):
            raise ValueError("Invalid token")

    async def get_channel(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a channel.

        Parameters:
            channel_id (int): The channel's ID.

        Returns:
            A dict representing the channel.

        """
        return await self.request("GET", f"/channels/{channel_id}")

    async def edit_text_channel(
        self,
        channel_id: int,
        *,
        name: Optional[str] = None,
        type: Optional[int] = None,
        position: Optional[int] = None,
        topic: Optional[str] = None,
        nsfw: Optional[bool] = None,
        rate_limit_per_user: Optional[int] = None,
        permission_overwrites: Optional[List[Dict[str, Any]]] = None,
        default_auto_archive_duration: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to edit a text channel.

        Parameters:
            channel_id (int): The channel id representing the channel to edit.
            name (Optional[str]): The new name for the channel.
            type (Optional[int]): The new type for the channel.
            position (Optional[int]): The new position for the channel.
            topic (Optional[str]): The new topic for the channel.
            nsfw (Optional[bool]): Whether or not the channel should be NSFW.
            rate_limit_per_user (Optional[int]): The new slowmode of the channel.
            permissions_overwrites (Optional[List[Dict[str, Any]]]): The new permission overwrites for the channel.
            default_auto_archive_duration (Optional[List[Dict[str, Any]]]): New time for threads to auto archive.

        """
        payload = update_payload(
            {},
            name=name,
            type=type,
            position=position,
            topic=topic,
            nsfw=nsfw,
            rate_limit_per_user=rate_limit_per_user,
            permission_overwrites=permission_overwrites,
            default_auto_archive_duration=default_auto_archive_duration,
        )
        return await self.request("PATCH", f"/channels/{channel_id}", json=payload)

    async def edit_voice_channel(
        self,
        channel_id: int,
        *,
        name: str = None,
        position: int = None,
        bitrate: int = None,
        user_limit: int = None,
        rtc_region: str = None,
        video_quality_mode: int = None,
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
        around: int = None,
        before: int = None,
        after: int = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        params = {"limit": limit}

        update_payload(params, around=around, before=before, after=after)

        return await self.request("GET", f"/channels/{channel_id}/messages", params=params)

    async def get_channel_message(self, channel_id: int, message_id: int) -> Dict[str, Any]:
        return await self.request("GET", f"/channels/{channel_id}/messages/{message_id}")

    async def send_message(
        self,
        channel_id: int,
        content: str = None,
        *,
        tts: bool = False,
        embeds: List[Dict[str, Any]] = None,
        allowed_mentions: Dict[str, Any] = None,
        message_reference: Dict[str, Any] = None,
        components: List[Dict[str, Any]] = None,
        sticker_ids: List[int] = None,
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

        return await self.request("POST", f"/channels/{channel_id}/messages", json=payload)

    async def crosspost_message(self, channel_id: int, message_id: int) -> Dict[str, Any]:
        return await self.request("POST", f"/channels/{channel_id}/messages/{message_id}/crosspost")

    async def create_reaction(self, channel_id: int, message_id: int, emoji: str):
        return await self.request(
            method="PUT",
            path=f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me",
        )

    async def delete_reaction(self, channel_id: int, message_id: int, emoji: str, user_id: int = None) -> None:
        if user_id is not None:
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
        after: int = None,
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
        return await self.request("DELETE", f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}")

    async def edit_message(
        self,
        channel_id: int,
        message_id: int,
        *,
        content: str = None,
        embeds: List[Dict[str, Any]] = None,
        flags: int = None,
        allowed_mentions: Dict[str, Any] = None,
        attachments: List[Dict[str, Any]] = None,
        components: List[Dict[str, Any]] = None,
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
        return await self.request("DELETE", f"/channels/{channel_id}/messages/{message_id}")

    async def bulk_delete_messages(self, channel_id: int, message_ids: List[int]):
        payload = {"messages": message_ids}
        return await self.request("POST", f"/channels/{channel_id}/messages/bulk-delete", json=payload)

    async def edit_channel_permissions(
        self,
        channel_id: int,
        overwrite_id: int,
        *,
        allow: int = None,
        deny: int = None,
        type: str = None,
    ):
        payload: dict = {}
        update_payload(payload, allow=allow, deny=deny, type=type)

        return await self.request(
            method="PUT",
            path=f"/channels/{channel_id}/permissions/{overwrite_id}",
            json=payload,
        )

    async def delete_channel_permissions(self, channel_id: int, overwrite_id: int):
        return await self.request("DELETE", f"/channels/{channel_id}/permissions/{overwrite_id}")

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
        target_type: int = None,
        target_user_id: int = None,
        target_application_id: int = None,
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

        return await self.request("POST", f"/channels/{channel_id}/invites", json=payload)

    async def follow_news_channel(self, channel_id: int, webhook_channel_id: int):
        payload = {"webhook_channel_id": webhook_channel_id}
        return await self.request("PUT", f"/channels/{channel_id}/followers/@me", json=payload)

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
        type: int = None,
        invitable: bool = None,
    ):
        payload = {"name": name, "auto_archive_duration": auto_archive_duration}
        update_payload(payload, type=type, invitable=invitable)

        return await self.request(method="POST", path=f"/channels/{channel_id}/threads", json=payload)

    async def join_thread(self, channel_id: int):
        return await self.request("PUT", f"/channels/{channel_id}/thread-members/@me")

    async def add_thread_member(self, channel_id: int, user_id: int):
        return await self.request("PUT", f"/channels/{channel_id}/thread-members/{user_id}")

    async def leave_thread(self, channel_id: int):
        return await self.request("DELETE", f"/channels/{channel_id}/thread-members/@me")

    async def remove_thread_member(self, channel_id: int, user_id: int):
        return await self.request("DELETE", f"/channels/{channel_id}/thread-members/{user_id}")

    async def list_thread_members(self, channel_id: int):
        return await self.request("GET", f"/channels/{channel_id}/thread-members")

    async def list_active_threads(self, channel_id: int):
        return await self.request("GET", f"/channels/{channel_id}/threads/active")

    async def list_public_archived_threads(self, channel_id: int, *, before: int = None, limit: int = None):
        params = update_payload({}, before=before, limit=limit)
        return await self.request("GET", f"/channels/{channel_id}/threads/archived/public", params=params)

    async def list_private_archived_threads(self, channel_id: int, *, before: int = None, limit: int = None):
        params = update_payload({}, before=before, limit=limit)
        return await self.request("GET", f"/channels/{channel_id}/threads/archived/private", params=params)

    async def list_joined_private_archived_threads(self, channel_id: int, *, before: int = None, limit: int = None):
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
        roles: List[int] = None,
    ) -> dict:
        payload = {
            "name": name,
            "image": image,
            "roles": [] if roles is None else roles,
        }

        return await self.request(method="POST", path=f"/guilds/{guild_id}/emojis", json=payload)

    async def modify_guild_emoji(self, guild_id: int, emoji_id: int, *, name: str, roles: List[int] = None) -> dict:
        payload = {
            "name": name,
        }
        update_payload(payload, roles=roles)

        return await self.request(method="PATCH", path=f"/guilds/{guild_id}/emojis/{emoji_id}", json=payload)

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
        name: str = None,
        permissions: int = None,
        color: int = None,
        hoist: bool = None,
        mentionable: bool = None,
    ) -> Dict[str, Any]:
        payload = update_payload(
            {},
            name=name,
            permissions=permissions,
            color=color,
            hoist=hoist,
            mentionable=mentionable,
        )

        return await self.request(method="PATCH", path=f"/guilds/{guild_id}/roles/{role_id}", json=payload)

    async def delete_guild_role(self, guild_id: int, role_id: int):
        return await self.request("DELETE", f"/guilds/{guild_id}/roles/{role_id}")

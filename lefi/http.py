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

    Danger:
        This class is used behind the scenes, **this is not intended to be called directly**.

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

        Returns:
            The data received from the API after making the call.

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
        name: Optional[str] = None,
        position: Optional[int] = None,
        bitrate: Optional[int] = None,
        user_limit: Optional[int] = None,
        rtc_region: Optional[str] = None,
        video_quality_mode: Optional[int] = None,
        sync_permissions: Optional[bool] = None,
        permissions_overwrites: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to edit a voice channel.

        Parameters:
            channel_id (int): The ID representing the voice channel to edit.
            name (Optional[str]): The new name to give the channel.
            position (Optional[int]): The new position of the channel.
            bitrate (Optional[int]): The new bitrate of the channel.
            user_limit (Optional[int]): The new user limit of the channel.
            rtc_region (Optional[str]): The new rtc region of the channel.
            video_quality_mode (Optional[int]): The new video quality of the channel.
            sync_permissions (Optional[bool]): Whether or not to sync the permissions.
            permissions_overwrites (Optional[List[Dict[str, Any]]]): The new permissions ovewrites for the channel.

        Returns:
            The data received from the API after the call.

        """
        payload = update_payload(
            {},
            name=name,
            position=position,
            bitrate=bitrate,
            user_limit=user_limit,
            rtc_region=rtc_region,
            video_quality_mode=video_quality_mode,
            sync_permissions=sync_permissions,
            permissions_overwrites=permissions_overwrites,
        )

        return await self.request("PATCH", f"/channels/{channel_id}", json=payload)

    async def get_channel_messages(
        self,
        channel_id: int,
        *,
        around: Optional[int] = None,
        before: Optional[int] = None,
        after: Optional[int] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Makes an API call to get a list of messages in a channel.
        Only returns messages within the range of the parameters passed.

        Parameters:
            channel_id (int): The ID representing the channel.
            around (Optional[int]): Gets messages around this message ID.
            before (Optional[int]): Gets messages before this message ID.
            after (Optional[int]): Gets messages after this message ID.
            limit (int): THe amount of messages to grab.

        Returns:
            The data received after making the call.

        """
        params = {"limit": limit}

        update_payload(params, around=around, before=before, after=after)

        return await self.request("GET", f"/channels/{channel_id}/messages", params=params)

    async def get_channel_message(self, channel_id: int, message_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a specific message by ID.

        Parameters:
            channel_id (int): The channel ID which the message is in.
            message_id (int): The messages ID.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("GET", f"/channels/{channel_id}/messages/{message_id}")

    async def send_message(
        self,
        channel_id: int,
        content: Optional[str] = None,
        *,
        tts: bool = False,
        embeds: Optional[List[Dict[str, Any]]] = None,
        allowed_mentions: Optional[Dict[str, Any]] = None,
        message_reference: Optional[Dict[str, Any]] = None,
        components: Optional[List[Dict[str, Any]]] = None,
        sticker_ids: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to send a message.

        Parameters:
            channel_id (int): The ID of the channel which to send the message in.
            content (Optional[str]): The content of the message.
            tts (bool): Whether or not to send the message with text-to-speech.
            embeds (Optional[List[Dict[str, Any]]]): The list of embeds to send.
            message_reference (Optional[Dict[str, Any]]): The messages to reference when sending the message.
            components (Optional[List[Dict[str, Any]]]): The components to attach to the message.
            sticker_ids (Optional[List[int]]): The stickers to send with the message.

        Note:
            Max embeds that can sent at a time is 10.

        """
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
        """
        Makes an API call to crosspost a message.

        Parameters:
            channel_id (int): The ID of the channel to crosspost to.
            message_id (int): The ID of the message which to crosspost.

        Returns:
            The data received after making the call.

        """
        return await self.request("POST", f"/channels/{channel_id}/messages/{message_id}/crosspost")

    async def create_reaction(self, channel_id: int, message_id: int, emoji: str):
        """
        Makes an API call to add a reaction to a message.

        Parameters:
            channel_id (int): The ID of the channel which the target message is in.
            message_id (int): The ID of the message which to add the reaction to.
            emoji (str): The emoji which to add.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            method="PUT",
            path=f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me",
        )

    async def delete_reaction(
        self,
        channel_id: int,
        message_id: int,
        emoji: str,
        user_id: Optional[int] = None,
    ) -> None:
        """
        Makes an API call to delete a reaction.

        Parameters:
            channel_id (int): The ID of the channel which the target message is in.
            message_id (int): The ID of the message.
            emoji (str): The emoji to remove from the message's reactions.
            user_id (Optional[int]): The ID of the user to remove from the reactions.

        Returns:
            The data received from the API after making the call.

        Note:
            If no user_id is given it will delete the client's reaction.

        """
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
        after: Optional[int] = None,
        limit: int = 25,
    ) -> Dict[str, Any]:
        """
        Makes an API call to get a list of users who reacted to a message..

        Parameters:
            channel_id (int): The ID of the channel which the target message is in.
            message_id (int): The ID of the message.
            emoji (str): The emoji from which to grab users from.
            after (int): Grab users after this user ID.
            limit (int): The max amount of users to grab.

        Returns:
            The data received from the API after making the call.

        """
        params = {"limit": limit}
        update_payload(params, after=after)
        return await self.request(
            method="GET",
            path=f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}",
            params=params,
        )

    async def delete_all_reactions(self, channel_id: int, message_id: int, emoji: str) -> Dict[str, Any]:
        """
        Makes an API call to remove all reactions of a message.

        Parameters:
            channel_id (int): The channel which the target message is in.
            message_id (int): The ID of the message.
            emoji (str): The reaction to remove.

        Returns:
            The data received from the API After making the call.

        """
        return await self.request("DELETE", f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}")

    async def edit_message(
        self,
        channel_id: int,
        message_id: int,
        *,
        content: Optional[str] = None,
        embeds: Optional[List[Dict[str, Any]]] = None,
        flags: Optional[int] = None,
        allowed_mentions: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to edit a message.

        Parameters:
            channel_id (int): The ID of the channel which the target message is in.
            message_id (int): The ID of the message.
            content (Optional[str]): The new content of the message.
            embeds (Optional[List[Dict[str, Any]]]): The new embeds of the message.
            flags (Optional[int]): The new flags of the message.
            allowed_mentions (Optional[int]): The new allowed mentions of the message.
            attachments (Optional[List[Dict[str, Any]]]): The new attachments of the message.
            components (Optional[List[Dict[str, Any]]]): The new components of the message.

        Returns:
            The data received from the API after making the call.

        """
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

    async def delete_message(self, channel_id: int, message_id: int) -> Dict[str, Any]:
        """
        Makes an API call to delete a message.

        Parameters:
            channel_id (int): The ID of the channel which the message is in.
            message_id (int): The ID Of the message.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("DELETE", f"/channels/{channel_id}/messages/{message_id}")

    async def bulk_delete_messages(self, channel_id: int, message_ids: List[int]) -> Dict[str, Any]:
        """
        Makes an API call to delete multiple messages.

        Parameters:
            channel_id (int): The ID of the channel which the message is in.
            message_ids (List[int]): The list of ID's representing messages of which to delete.

        Returns:
            The data received from the API after making the call.

        """
        payload = {"messages": message_ids}
        return await self.request("POST", f"/channels/{channel_id}/messages/bulk-delete", json=payload)

    async def edit_channel_permissions(
        self,
        channel_id: int,
        overwrite_id: int,
        *,
        allow: Optional[int] = None,
        deny: Optional[int] = None,
        type: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to edit a channels permissions.

        Parameters:
            channel_id (int): The ID of the channel.
            overwrite_id (int): The ID of the overwrite.
            allow (Optional[int]): The bitwise value of all allowed permissions.
            deny (Optional[int]): The bitwise value of all denied permissison.
            type (Optional[int]): The type, 0 being a role and 1 being a member.

        Returns:
            The data received from the API after making the call.

        """
        payload: dict = {}
        update_payload(payload, allow=allow, deny=deny, type=type)

        return await self.request(
            method="PUT",
            path=f"/channels/{channel_id}/permissions/{overwrite_id}",
            json=payload,
        )

    async def delete_channel_permissions(self, channel_id: int, overwrite_id: int) -> Dict[str, Any]:
        """
        Makes an API call to delete an overwrite from a channel.

        Parameters:
            channel_id (int): The ID of the channel.
            overwrite_id (int): The ID of the overwrite.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("DELETE", f"/channels/{channel_id}/permissions/{overwrite_id}")

    async def get_channel_invites(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a channels invites.

        Parameters:
            channel_id (int): The ID of the channel.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("GET", f"/channels/{channel_id}/invites")

    async def create_channel_invite(
        self,
        channel_id: int,
        *,
        max_age: int = 86400,
        max_uses: int = 0,
        temporary: bool = False,
        unique: bool = False,
        target_type: Optional[int] = None,
        target_user_id: Optional[int] = None,
        target_application_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create an invite.

        Parameters:
            channel_id (int): The ID of the channel.
            max_age (int): The max age of the invite.
            max_uses (int): The max uses of the invite. 0 if unlimited.
            temporary (bool): Whether or not the invite is temporary.
            unique (bool): Whether or not the invite is unique.
            target_type (Optional[int]): The type of the invite. For voice channels.
            target_user_id (Optional[int]): The ID of the user whose stream to invite to. For voice channels.
            target_application_id (Optional[int]): The ID of embedded application to invite from. For target type 2.

        Returns:
            The data received from the API after making the call.

        """
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

    async def follow_news_channel(self, channel_id: int, webhook_channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to follow a news channel to send messages to a target channel.

        Parameters:
            channel_id (int): The ID Of the channel.
            webhook_channel_id (int): The target channel.

        Returns:
            The data received from the API after making the call.

        """
        payload = {"webhook_channel_id": webhook_channel_id}
        return await self.request("PUT", f"/channels/{channel_id}/followers/@me", json=payload)

    async def trigger_typing(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to trigger typing.

        Parameters:
            channel_id (int): The ID of the channel which to trigger typing in.

        Returns:
            The data received from the API After making the call.

        """
        return await self.request("POST", f"/channels/{channel_id}/typing")

    async def get_pinned_messages(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get the pinned messages of a channel.

        Parameters:
            channel_id (int): The ID of the channel which to grab pinned messages from.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("GET", f"/channels/{channel_id}/pins")

    async def pin_message(self, channel_id: int, message_id: int) -> Dict[str, Any]:
        """
        Makes an API call to pin a message.

        Parameters:
            channel_id (int): The ID of the channel where the message is.
            message_id (int): The ID of the message.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("PUT", f"/channels/{channel_id}/pins/{message_id}")

    async def unpin_message(self, channel_id: int, message_id: int) -> Dict[str, Any]:
        """
        Makes an API call to unpin a message.

        Parameters:
            channel_id (int): The ID Of the channel where the message is.
            message_id (int): The ID of the message.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("DELETE", f"/channels/{channel_id}/pins/{message_id}")

    async def start_thread_with_message(
        self, channel_id: int, message_id: int, *, name: str, auto_archive_duration: int
    ) -> Dict[str, Any]:
        """
        Makes an API call to start a thread with a message.

        Parameters:
            channel_id (int): The ID of the channel which the message is in.
            message_id (int): The ID Of the message.
            name (str): The name of the thread.
            auto_archive_duration (int): The time it takes to auto archive the thread.

        Returns:
            The data received from the API after making the call.

        """
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
        type: Optional[int] = None,
        invitable: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to start a thread without a message.

        Parameters:
            channel_id (int): The ID of the channel where the thread will be created.
            name (str): The name of the thread.
            auto_archive_duration (int): The time it takes to auto archive the thread.
            type (int): The type of the thread to create.
            invitable (bool): Whether or not members can invite other members to the thread. Only in private threads.

        Returns:
            The data received from the API after making the call.

        """
        payload = {"name": name, "auto_archive_duration": auto_archive_duration}
        update_payload(payload, type=type, invitable=invitable)

        return await self.request(method="POST", path=f"/channels/{channel_id}/threads", json=payload)

    async def join_thread(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call which makes the client join the given thread.

        Parameters:
            channel_id (int): The ID of the thread.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("PUT", f"/channels/{channel_id}/thread-members/@me")

    async def add_thread_member(self, channel_id: int, user_id: int) -> Dict[str, Any]:
        """
        Makes an API call which adds another member to the thread.

        Parameters:
            channel_id (int): The ID of the thread.
            user_id (int): The ID of the user to add.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("PUT", f"/channels/{channel_id}/thread-members/{user_id}")

    async def leave_thread(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call which makes the client leave the thread.

        Parameters:
            channel_id (int): The ID of the thread.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("DELETE", f"/channels/{channel_id}/thread-members/@me")

    async def remove_thread_member(self, channel_id: int, user_id: int) -> Dict[str, Any]:
        """
        Makes an API call which removes a member from the thread.

        Parameters:
            channel_id (int): The ID of the thread.
            user_id (int): The ID of the user to remove.

        Returns:
            The data received from the API after making the call

        """
        return await self.request("DELETE", f"/channels/{channel_id}/thread-members/{user_id}")

    async def list_thread_members(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get all of the members of a thread.

        Parameters:
            channel_id (int): The ID of the thread.

        Returns:
            The data received from the API after making the call

        """
        return await self.request("GET", f"/channels/{channel_id}/thread-members")

    async def list_public_archived_threads(
        self,
        channel_id: int,
        *,
        before: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call which list all the public archived threads in the channel.

        Parameters:
            channel_id (int): The ID of the channel which the threads are inside of.
            before (Optional[int]): Grab threads before this time.
            limit (Optional[int]): The amount of threads to grab.

        Returns:
            The data received from the API after making the call

        """
        params = update_payload({}, before=before, limit=limit)
        return await self.request("GET", f"/channels/{channel_id}/threads/archived/public", params=params)

    async def list_private_archived_threads(
        self,
        channel_id: int,
        *,
        before: Optional[int] = None,
        limit: Optional[int] = None,
    ):
        """
        Makes an API call which list all the private archived threads in the channel.

        Parameters:
            channel_id (int): The ID of the channel which the threads are inside of.
            before (Optional[int]): Grab threads before this time.
            limit (Optional[int]): The amount of threads to grab.

        Returns:
            The data received from the API after making the call

        """
        params = update_payload({}, before=before, limit=limit)
        return await self.request("GET", f"/channels/{channel_id}/threads/archived/private", params=params)

    async def list_joined_private_archived_threads(
        self,
        channel_id: int,
        *,
        before: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call which list all the private archived threads in the channel which the client has joined.

        Parameters:
            channel_id (int): The ID of the channel which the threads are inside of.
            before (Optional[int]): Grab threads before this time.
            limit (Optional[int]): The amount of threads to grab.

        Returns:
            The data received from the API after making the call

        """
        params = update_payload({}, before=before, limit=limit)
        return await self.request(
            "GET",
            f"/channels/{channel_id}/users/@me/threads/archived/private",
            params=params,
        )

    async def list_guild_emojis(self, guild_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a list of the guilds emojis.

        Parameters:
            guild_id (int): The ID of the guild to grab from.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("GET", f"/guilds/{guild_id}/emojis")

    async def get_guild_emoji(self, guild_id: int, emoji_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get an emoji from the guild.

        Parameters:
            guild_id (int): The ID of the guild to grab from.
            emoji_id (int): The ID of the emoji to get.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("GET", f"/guilds/{guild_id}/emojis/{emoji_id}")

    async def create_guild_emoji(
        self,
        guild_id: int,
        *,
        name: str,
        image: str,
        roles: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create an emoji.

        Parameters:
            guild_id (int): The ID of the guild to create the emoji in.
            name (str): The name of the emoji.
            image (str): The image of the emoji.
            roles (Optional[List[int]]): The list of roles that can use this emoji.

        Returns:
            The data received from the API after making the call.

        """
        payload = {
            "name": name,
            "image": image,
            "roles": [] if roles is None else roles,
        }

        return await self.request(method="POST", path=f"/guilds/{guild_id}/emojis", json=payload)

    async def modify_guild_emoji(
        self,
        guild_id: int,
        emoji_id: int,
        *,
        name: str,
        roles: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to edit an emoji.

        Parameters:
            guild_id (int): The ID of the guild where the emoji is.
            emoji_id (int): The ID of the emoji.
            name (str): The new name of the emoji.
            roles (Optional[List[int]]): The new list of roles that can use this emoji.

        Returns:
            The data received from the API after making the call.

        """
        payload = {
            "name": name,
        }
        update_payload(payload, roles=roles)

        return await self.request(method="PATCH", path=f"/guilds/{guild_id}/emojis/{emoji_id}", json=payload)

    async def delete_guild_emoji(self, guild_id: int, emoji_id: int) -> Dict[str, Any]:
        """
        Makes an API call which deletes an emoji.

        Parameters:
            guild_id (int): The ID of the guild where the emoji is in.
            emoji_id (int): The ID of the emoji to delete.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("DELETE", f"/guilds/{guild_id}/emojis/{emoji_id}")

    async def create_dm_channel(self, recipient_id: int) -> Dict[str, Any]:
        """
        Makes an API call which creates a DM channel to a user.

        Parameters:
            recipient_id (int): The ID of the user which to open the DM channel to.

        Returns:
            The data received from the API after making the call.

        """
        payload = {"recipient_id": recipient_id}
        return await self.request("POST", "/users/@me/channels", json=payload)

    async def modifiy_guild_role(
        self,
        guild_id: int,
        role_id: int,
        *,
        name: Optional[str] = None,
        permissions: Optional[int] = None,
        color: Optional[int] = None,
        hoist: Optional[bool] = None,
        mentionable: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call which edits a role.

        Parameters:
            guild_id (int): The ID of the guild where the role is.
            role_id (int): The ID of the role.
            name (Optional[str]): The new name of the role.
            permissions (Optional[int]): The new permissions of the role.
            color (Optional[int]): The new color of the role.
            hoist (Optional[bool]): Whether or not to hoist the role.
            mentionable (Optional[bool]): Whether or not the role should be mentionable.

        Returns:
            The data received from the API after making the call.

        """
        payload = update_payload(
            {},
            name=name,
            permissions=permissions,
            color=color,
            hoist=hoist,
            mentionable=mentionable,
        )

        return await self.request(method="PATCH", path=f"/guilds/{guild_id}/roles/{role_id}", json=payload)

    async def delete_guild_role(self, guild_id: int, role_id: int) -> Dict[str, Any]:
        """
        Makes an API call which deletes a role.

        Parameters:
            guild_id (int): The ID of the guild where the role is.
            role_id (int): The ID of the role.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request("DELETE", f"/guilds/{guild_id}/roles/{role_id}")

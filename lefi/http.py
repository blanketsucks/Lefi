from __future__ import annotations

import asyncio
import contextlib
import datetime
import io
import json
import logging
from typing import Any, ClassVar, Dict, List, Optional, Union

import aiohttp

from .errors import BadRequest, Forbidden, HTTPException, NotFound, Unauthorized
from .ratelimiter import Ratelimiter
from .utils import bytes_to_data_uri, update_payload

__all__ = (
    "HTTPClient",
    "Route",
)

logger = logging.getLogger(__name__)

BASE: str = "https://discord.com/api/v9"


class Route:
    def __init__(self, path: str, **kwargs) -> None:
        self.params: Dict = kwargs
        self.path: str = path

        self.channel_id: Optional[int] = kwargs.get("channel_id")
        self.guild_id: Optional[int] = kwargs.get("guild_id")
        self.webhook_id: Optional[int] = kwargs.get("webhook_id")
        self.webhook_token: Optional[str] = kwargs.get("webhookd_token")

        self.lock: asyncio.Lock = asyncio.Lock()

    @property
    def url(self) -> str:
        return f"{BASE+self.path}"

    @property
    def bucket(self) -> str:
        return f"{self.channel_id}:{self.guild_id}:{self.webhook_id}:{self.path}"


class HTTPClient:
    """
    A class used to send and handle requests to the discord API.

    Attributes:
        token (str): The clients token, used for authorization.
        loop (asyncio.AbstractEventLoop): The [asyncio.AbstractEventLoop][] being used.
        session (aiohttp.ClientSession): The [aiohttp.ClientSession][] to use for sending requests.

    Danger:
        This class is used internally, **this is not intended to be called directly**.

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
        self.semaphores: Dict[str, asyncio.Semaphore] = {}

    @staticmethod
    async def json_or_text(resp: aiohttp.ClientResponse) -> Union[dict, str]:
        try:
            return await resp.json()
        except aiohttp.ContentTypeError:
            return await resp.text()

    async def _create_session(
        self, loop: asyncio.AbstractEventLoop = None
    ) -> aiohttp.ClientSession:
        """
        Creates the session to use if one wasn't given during construction.

        Parameters:
            loop (asyncio.AbstractEventLoop): The [asyncio.AbstractEventLoop][] to use for the session.

        Returns:
            The created [aiohttp.ClientSession][] instance.

        """
        return aiohttp.ClientSession(loop=self.loop or loop)

    async def request(self, method: str, route: Route, **kwargs) -> Any:
        """
        Makes a request to the discord API.

        Parameters:
            method (str): The method for the request.
            route (lefi.Route): The endpoint which to send the request to.
            **kwargs (Any): Any extra options to pass to [aiohttp.ClientSession.request][]

        Returns:
            The data returned from the request.

        Raises:
            [lefi.errors.HTTPException][] if any error was received from the request.

        """

        if self.session is None or self.session.closed:
            self.session = await self._create_session()

        headers: Dict = {"Authorization": f"Bot {self.token}"}
        if reason := kwargs.get("reason"):
            headers["X-Audit-Log-Reason"] = reason

        if form := kwargs.pop("form", []):
            formdata = aiohttp.FormData()
            payload = kwargs.pop("json", None)

            if payload:
                formdata.add_field("payload_json", value=json.dumps(payload))

            for params in form:
                formdata.add_field(**params)

            kwargs["data"] = formdata

        async with Ratelimiter(
            self, route, method, **kwargs, headers=headers
        ) as handler:
            return await handler.request()

    async def get_bot_gateway(self) -> Dict:
        """
        A method which gets the gateway url.

        Returns:
            A dict which should contain the url.

        """
        return await self.request("GET", Route("/gateway/bot"))

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
            await self.get_current_user()
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
        return await self.request(
            "GET", Route(f"/channels/{channel_id}", channel_id=channel_id)
        )

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
        return await self.request(
            "PATCH",
            Route(f"/channels/{channel_id}", channel_id=channel_id),
            json=payload,
        )

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

        return await self.request(
            "PATCH",
            Route(f"/channels/{channel_id}", channel_id=channel_id),
            json=payload,
        )

    async def get_channel_messages(
        self,
        channel_id: int,
        *,
        around: Optional[int] = None,
        before: Optional[int] = None,
        after: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
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

        return await self.request(
            "GET",
            Route(f"/channels/{channel_id}/messages", channel_id=channel_id),
            params=params,
        )

    async def get_channel_message(
        self, channel_id: int, message_id: int
    ) -> Dict[str, Any]:
        """
        Makes an API call to get a specific message by ID.

        Parameters:
            channel_id (int): The channel ID which the message is in.
            message_id (int): The messages ID.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            "GET",
            Route(
                f"/channels/{channel_id}/messages/{message_id}", channel_id=channel_id
            ),
        )

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
        files: Optional[List[io.BufferedIOBase]] = None,
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

        files = files or []
        form = []

        for index, file in enumerate(files):
            form.append(
                {
                    "name": f"file-{index}",
                    "value": file,
                    "filename": getattr(file, "name", None),
                    "content_type": "application/octect-stream",
                }
            )

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
            "POST",
            Route(f"/channels/{channel_id}/messages", channel_id=channel_id),
            json=payload,
            form=form,
        )

    async def crosspost_message(
        self, channel_id: int, message_id: int
    ) -> Dict[str, Any]:
        """
        Makes an API call to crosspost a message.

        Parameters:
            channel_id (int): The ID of the channel to crosspost to.
            message_id (int): The ID of the message which to crosspost.

        Returns:
            The data received after making the call.

        """
        return await self.request(
            "POST",
            Route(
                f"/channels/{channel_id}/messages/{message_id}/crosspost",
                channel_id=channel_id,
            ),
        )

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
            "PUT",
            Route(
                f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me",
                channel_id=channel_id,
            ),
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

        await self.request("DELETE", Route(path, channel_id=channel_id))

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
            "GET",
            Route(
                f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}",
                channel_id=channel_id,
            ),
            params=params,
        )

    async def delete_all_reactions(
        self, channel_id: int, message_id: int, emoji: str
    ) -> Dict[str, Any]:
        """
        Makes an API call to remove all reactions of a message.

        Parameters:
            channel_id (int): The channel which the target message is in.
            message_id (int): The ID of the message.
            emoji (str): The reaction to remove.

        Returns:
            The data received from the API After making the call.

        """
        return await self.request(
            "DELETE",
            Route(
                f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}",
                channel_id=channel_id,
            ),
        )

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
            "PATCH",
            Route(
                f"/channels/{channel_id}/messages/{message_id}", channel_id=channel_id
            ),
            json=payload,
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
        return await self.request(
            "DELETE",
            Route(
                f"/channels/{channel_id}/messages/{message_id}", channel_id=channel_id
            ),
        )

    async def bulk_delete_messages(
        self, channel_id: int, message_ids: List[int]
    ) -> Dict[str, Any]:
        """
        Makes an API call to delete multiple messages.

        Parameters:
            channel_id (int): The ID of the channel which the message is in.
            message_ids (List[int]): The list of ID's representing messages of which to delete.

        Returns:
            The data received from the API after making the call.

        """
        payload = {"messages": message_ids}
        return await self.request(
            "POST",
            Route(
                f"/channels/{channel_id}/messages/bulk-delete", channel_id=channel_id
            ),
            json=payload,
        )

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
            "PUT",
            Route(
                f"/channels/{channel_id}/permissions/{overwrite_id}",
                channel_id=channel_id,
            ),
            json=payload,
        )

    async def delete_channel_permissions(
        self, channel_id: int, overwrite_id: int
    ) -> Dict[str, Any]:
        """
        Makes an API call to delete an overwrite from a channel.

        Parameters:
            channel_id (int): The ID of the channel.
            overwrite_id (int): The ID of the overwrite.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            "DELETE",
            Route(
                f"/channels/{channel_id}/permissions/{overwrite_id}",
                channel_id=channel_id,
            ),
        )

    async def get_channel_invites(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a channels invites.

        Parameters:
            channel_id (int): The ID of the channel.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            "GET", Route(f"/channels/{channel_id}/invites", channel_id=channel_id)
        )

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

        return await self.request(
            "POST",
            Route(f"/channels/{channel_id}/invites", channel_id=channel_id),
            json=payload,
        )

    async def follow_news_channel(
        self, channel_id: int, webhook_channel_id: int
    ) -> Dict[str, Any]:
        """
        Makes an API call to follow a news channel to send messages to a target channel.

        Parameters:
            channel_id (int): The ID Of the channel.
            webhook_channel_id (int): The target channel.

        Returns:
            The data received from the API after making the call.

        """
        payload = {"webhook_channel_id": webhook_channel_id}
        return await self.request(
            "PUT",
            Route(f"/channels/{channel_id}/followers/@me", channel_id=channel_id),
            json=payload,
        )

    async def trigger_typing(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to trigger typing.

        Parameters:
            channel_id (int): The ID of the channel which to trigger typing in.

        Returns:
            The data received from the API After making the call.

        """
        return await self.request(
            "POST", Route(f"/channels/{channel_id}/typing", channel_id=channel_id)
        )

    async def get_pinned_messages(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get the pinned messages of a channel.

        Parameters:
            channel_id (int): The ID of the channel which to grab pinned messages from.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            "GET", Route(f"/channels/{channel_id}/pins", channel_id=channel_id)
        )

    async def pin_message(self, channel_id: int, message_id: int) -> Dict[str, Any]:
        """
        Makes an API call to pin a message.

        Parameters:
            channel_id (int): The ID of the channel where the message is.
            message_id (int): The ID of the message.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            "PUT",
            Route(f"/channels/{channel_id}/pins/{message_id}", channel_id=channel_id),
        )

    async def unpin_message(self, channel_id: int, message_id: int) -> Dict[str, Any]:
        """
        Makes an API call to unpin a message.

        Parameters:
            channel_id (int): The ID Of the channel where the message is.
            message_id (int): The ID of the message.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            "DELETE",
            Route(f"/channels/{channel_id}/pins/{message_id}", channel_id=channel_id),
        )

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
            "POST",
            Route(
                f"/channels/{channel_id}/messages/{message_id}/threads",
                channel_id=channel_id,
            ),
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

        return await self.request(
            "POST",
            Route(f"/channels/{channel_id}/threads", channel_id=channel_id),
            json=payload,
        )

    async def join_thread(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call which makes the client join the given thread.

        Parameters:
            channel_id (int): The ID of the thread.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            "PUT",
            Route(f"/channels/{channel_id}/thread-members/@me", channel_id=channel_id),
        )

    async def add_thread_member(self, channel_id: int, user_id: int) -> Dict[str, Any]:
        """
        Makes an API call which adds another member to the thread.

        Parameters:
            channel_id (int): The ID of the thread.
            user_id (int): The ID of the user to add.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            "PUT",
            Route(
                f"/channels/{channel_id}/thread-members/{user_id}",
                channel_id=channel_id,
            ),
        )

    async def leave_thread(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call which makes the client leave the thread.

        Parameters:
            channel_id (int): The ID of the thread.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            "DELETE",
            Route(f"/channels/{channel_id}/thread-members/@me", channel_id=channel_id),
        )

    async def remove_thread_member(
        self, channel_id: int, user_id: int
    ) -> Dict[str, Any]:
        """
        Makes an API call which removes a member from the thread.

        Parameters:
            channel_id (int): The ID of the thread.
            user_id (int): The ID of the user to remove.

        Returns:
            The data received from the API after making the call

        """
        return await self.request(
            "DELETE",
            Route(
                f"/channels/{channel_id}/thread-members/{user_id}",
                channel_id=channel_id,
            ),
        )

    async def list_thread_members(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get all of the members of a thread.

        Parameters:
            channel_id (int): The ID of the thread.

        Returns:
            The data received from the API after making the call

        """
        return await self.request(
            "GET",
            Route(f"/channels/{channel_id}/thread-members", channel_id=channel_id),
        )

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
        return await self.request(
            "GET",
            Route(
                f"/channels/{channel_id}/threads/archived/public", channel_id=channel_id
            ),
            params=params,
        )

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
        return await self.request(
            "GET",
            Route(
                f"/channels/{channel_id}/threads/archived/private",
                channel_id=channel_id,
            ),
            params=params,
        )

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
            Route(
                f"/channels/{channel_id}/users/@me/threads/archived/private",
                channel_id=channel_id,
            ),
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
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/emojis", guild_id=guild_id)
        )

    async def get_guild_emoji(self, guild_id: int, emoji_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get an emoji from the guild.

        Parameters:
            guild_id (int): The ID of the guild to grab from.
            emoji_id (int): The ID of the emoji to get.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/emojis/{emoji_id}", guild_id=guild_id)
        )

    async def create_guild_emoji(
        self,
        guild_id: int,
        *,
        name: str,
        image: bytes,
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
            "image": bytes_to_data_uri(image),
            "roles": [] if roles is None else roles,
        }

        return await self.request(
            "POST",
            Route(f"/guilds/{guild_id}/emojis", guild_id=guild_id),
            json=payload,
        )

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
        payload = {"name": name}
        update_payload(payload, roles=roles)

        return await self.request(
            "PATCH",
            Route(f"/guilds/{guild_id}/emojis/{emoji_id}", guild_id=guild_id),
            json=payload,
        )

    async def delete_guild_emoji(self, guild_id: int, emoji_id: int) -> Dict[str, Any]:
        """
        Makes an API call which deletes an emoji.

        Parameters:
            guild_id (int): The ID of the guild where the emoji is in.
            emoji_id (int): The ID of the emoji to delete.

        Returns:
            The data received from the API after making the call.

        """
        return await self.request(
            "DELETE", Route(f"/guilds/{guild_id}/emojis/{emoji_id}", guild_id=guild_id)
        )

    async def create_guild(
        self,
        name: str,
        *,
        region: Optional[str] = None,
        icon: Optional[bytes] = None,
        verification_level: Optional[int] = None,
        default_message_notifications: Optional[int] = None,
        explicit_content_filter: Optional[int] = None,
        roles: Optional[List[Dict[str, Any]]] = None,
        channels: Optional[List[Dict[str, Any]]] = None,
        afk_channel: Optional[int] = None,
        afk_timeout: Optional[int] = None,
        system_channel_id: Optional[int] = None,
        system_channel_flags: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create a guild.

        Parameters:
            name (str): The name of the guild.
            region (Optional[str]): The region of the guild.
            icon (Optional[str]): The icon of the guild.
            verification_level (Optional[int]): The verification level of the guild.
            default_message_notifications (Optional[int]): The default message notifications of the guild.
            explicit_content_filter (Optional[int]): The explicit content filter of the guild.
            roles (Optional[List[Dict[str, Any]]]): The list of roles to create.
            channels (Optional[List[Dict[str, Any]]]]): The list of channels to create.
            afk_channel (Optional[int]): The ID of the AFK channel.
            afk_timeout (Optional[int]): The AFK timeout of the guild.
            system_channel_id (Optional[int]): The ID of the system channel.
            system_channel_flags (Optional[int]): The flags of the system channel.

        Returns:
            The data received from the API after making the call.

        """
        payload = update_payload(
            {},
            name=name,
            region=region,
            icon=icon,
            verification_level=verification_level,
            default_message_notifications=default_message_notifications,
            explicit_content_filter=explicit_content_filter,
            roles=roles,
            channels=channels,
            afk_channel=afk_channel,
            afk_timeout=afk_timeout,
            system_channel_id=system_channel_id,
            system_channel_flags=system_channel_flags,
        )

        if "icon" in payload:
            payload["icon"] = bytes_to_data_uri(payload["icon"])

        return await self.request("POST", Route("/guilds"), json=payload)

    async def get_guild(
        self, guild_id: int, *, with_counts: bool = False
    ) -> Dict[str, Any]:
        """
        Makes an API call to get a guild.

        Parameters:
            guild_id (int): The ID of the guild to get.

        Returns:
            The data received from the API after making the call.

        """
        params = {"with_counts": with_counts}
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}", guild_id=guild_id), params=params
        )

    async def get_guild_preview(self, guild_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a guild's preview.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/preview", guild_id=guild_id)
        )

    async def modify_guild(
        self,
        guild_id: int,
        *,
        name: Optional[str] = None,
        region: Optional[str] = None,
        verification_level: Optional[int] = None,
        default_message_notifications: Optional[int] = None,
        afk_channel: Optional[int] = None,
        afk_timeout: Optional[int] = None,
        icon: Optional[bytes] = None,
        owner_id: Optional[int] = None,
        splash: Optional[bytes] = None,
        discovery_splash: Optional[bytes] = None,
        banner: Optional[bytes] = None,
        system_channel_id: Optional[int] = None,
        system_channel_flags: Optional[int] = None,
        rules_channel_id: Optional[int] = None,
        public_updates_channel_id: Optional[int] = None,
        preferred_locale: Optional[str] = None,
        features: Optional[List[str]] = None,
        description: Optional[str] = None,
    ):
        """
        Makes an API call to modify a guild.

        Parameters
            guild_id (int): The ID of the guild to edit.
            name (Optional[str]): The name of the guild.
            region (Optional[str]): The region of the guild.
            verification_level (Optional[int]): The verification level of the guild.
            default_message_notifications (Optional[int]): The default message notifications of the guild.
            afk_channel (Optional[int]): The AFK channel of the guild.
            afk_timeout (Optional[int]): The AFK timeout of the guild.
            icon (Optional[str]): The icon of the guild.
            owner_id (Optional[int]): The ID of the owner of the guild.
            splash (Optional[str]): The splash of the guild.
            discovery_splash (Optional[str]): The discovery splash of the guild.
            banner (Optional[str]): The banner of the guild.
            system_channel_id (Optional[int]): The ID of the system channel of the guild.
            system_channel_flags (Optional[int]): The flags of the system channel of the guild.
            rules_channel_id (Optional[int]): The ID of the rules channel of the guild.
            public_updates_channel_id (Optional[int]): The ID of the public updates channel of the guild.
            preferred_locale (Optional[str]): The preferred locale of the guild.
            features (Optional[List[str]]): The features of the guild.
            description (Optional[str]): The description of the guild.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {},
            name=name,
            region=region,
            verification_level=verification_level,
            default_message_notifications=default_message_notifications,
            afk_channel=afk_channel,
            afk_timeout=afk_timeout,
            icon=icon,
            owner_id=owner_id,
            splash=splash,
            discovery_splash=discovery_splash,
            banner=banner,
            system_channel_id=system_channel_id,
            system_channel_flags=system_channel_flags,
            rules_channel_id=rules_channel_id,
            public_updates_channel_id=public_updates_channel_id,
            preferred_locale=preferred_locale,
            features=features,
            description=description,
        )

        if "icon" in payload:
            payload["icon"] = bytes_to_data_uri(payload["icon"])

        if "splash" in payload:
            payload["splash"] = bytes_to_data_uri(payload["splash"])

        if "discovery_splash" in payload:
            payload["discovery_splash"] = bytes_to_data_uri(payload["discovery_splash"])

        if "banner" in payload:
            payload["banner"] = bytes_to_data_uri(payload["banner"])

        return await self.request(
            "PATCH", Route(f"/guilds/{guild_id}", guild_id=guild_id), json=payload
        )

    async def delete_guild(self, guild_id: int):
        """
        Makes an API call to delete a guild.

        Parameters:
            guild_id (int): The ID of the guild to delete.

        """
        await self.request("DELETE", Route(f"/guilds/{guild_id}", guild_id=guild_id))

    async def get_guild_channels(self, guild_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a guild's channels.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/channels", guild_id=guild_id)
        )

    async def create_guild_channel(
        self,
        guild_id: int,
        name: str,
        *,
        type: Optional[int] = None,
        topic: Optional[str] = None,
        bitrate: Optional[int] = None,
        user_limit: Optional[int] = None,
        position: Optional[int] = None,
        permission_overwrites: Optional[List[Dict[str, Any]]] = None,
        parent_id: Optional[int] = None,
        nsfw: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create a channel in a guild.

        Parameters
            guild_id (int): The ID of the guild.
            name (str): The name of the channel.
            type (Optional[int]): The type of the channel.
            topic (Optional[str]): The topic of the channel.
            bitrate (Optional[int]): The bitrate of the channel.
            user_limit (Optional[int]): The user limit of the channel.
            position (Optional[int]): The position of the channel.
            permission_overwrites (Optional[List[Dict[str, Any]]]): The permission overwrites of the channel.
            parent_id (Optional[int]): The ID of the parent of the channel.
            nsfw (Optional[bool]): Whether the channel is NSFW.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {},
            name=name,
            type=type,
            topic=topic,
            bitrate=bitrate,
            user_limit=user_limit,
            position=position,
            permission_overwrites=permission_overwrites,
            parent_id=parent_id,
            nsfw=nsfw,
        )

        return await self.request(
            "POST",
            Route(f"/guilds/{guild_id}/channels", guild_id=guild_id),
            json=payload,
        )

    async def list_active_threads(self, guild_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a guild's active threads.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/threads/active", guild_id=guild_id)
        )

    async def get_guild_member(self, guild_id: int, member_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a guild member.

        Parameters:
            guild_id (int): The ID of the guild.
            member_id (int): The ID of the member.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/members/{member_id}", guild_id=guild_id)
        )

    async def list_guild_members(
        self, guild_id: int, *, limit: int = 1, after: int = 0
    ) -> Dict[str, Any]:
        """
        Makes an API call to get a guild's members.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        params = {"limit": limit, "after": after}
        return await self.request(
            "GET",
            Route(f"/guilds/{guild_id}/members", guild_id=guild_id),
            params=params,
        )

    async def search_guild_members(
        self, guild_id: int, *, query: str, limit: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Makes an API call to search a guild's members.

        Parameters:
            guild_id (int): The ID of the guild.
            query (str): The query to search for.
            limit (Optional[int]): The number of members to return.

        Returns:
            The data returned from the API.

        """
        params = {"limit": limit, "query": query}
        return await self.request(
            "GET",
            Route(f"/guilds/{guild_id}/members/search", guild_id=guild_id),
            params=params,
        )

    async def add_guild_member(
        self,
        guild_id: int,
        member_id: int,
        access_token: str,
        *,
        nick: Optional[str] = None,
        roles: Optional[List[int]] = None,
        mute: Optional[bool] = None,
        deaf: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to add a member to a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            member_id (int): The ID of the member.
            access_token (str): An oauth2 access token.
            nick (Optional[str]): The nickname of the member.
            roles (Optional[List[int]]): The roles of the member.
            mute (Optional[bool]): Whether the member is muted.
            deaf (Optional[bool]): Whether the member is deafened.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {}, access_token=access_token, nick=nick, roles=roles, mute=mute, deaf=deaf
        )
        return await self.request(
            "PUT",
            Route(f"/guilds/{guild_id}/members/{member_id}", guild_id=guild_id),
            json=payload,
        )

    async def edit_guild_member(
        self,
        guild_id: int,
        member_id: int,
        *,
        nick: Optional[str] = None,
        roles: Optional[List[int]] = None,
        mute: Optional[bool] = None,
        deaf: Optional[bool] = None,
        channel_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to edit a member in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            member_id (int): The ID of the member.
            nick (Optional[str]): The nickname of the member.
            roles (Optional[List[int]]): The roles of the member.
            mute (Optional[bool]): Whether the member is muted.
            deaf (Optional[bool]): Whether the member is deafened.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {}, nick=nick, roles=roles, mute=mute, deaf=deaf, channel_id=channel_id
        )
        return await self.request(
            "PATCH",
            Route(f"/guilds/{guild_id}/members/{member_id}", guild_id=guild_id),
            json=payload,
        )

    async def edit_current_member(self, guild_id: int, *, nick: Optional[str] = None):
        """
        Makes an API call to edit the current userin a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            nick (Optional[str]): The nickname of the member.

        Returns:
            The data returned from the API.

        """
        payload = update_payload({}, nick=nick)
        return await self.request(
            "PATCH",
            Route(f"/users/@me/guilds/{guild_id}", guild_id=guild_id),
            json=payload,
        )

    async def add_guild_member_role(self, guild_id: int, member_id: int, role_id: int):
        """
        Makes an API call to add a role to a member in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            member_id (int): The ID of the member.
            role_id (int): The ID of the role.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "PUT",
            Route(
                f"/guilds/{guild_id}/members/{member_id}/roles/{role_id}",
                guild_id=guild_id,
            ),
        )

    async def remove_guild_member_role(
        self, guild_id: int, member_id: int, role_id: int
    ):
        """
        Makes an API call to remove a role from a member in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            member_id (int): The ID of the member.
            role_id (int): The ID of the role.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "DELETE",
            Route(
                f"/guilds/{guild_id}/members/{member_id}/roles/{role_id}",
                guild_id=guild_id,
            ),
        )

    async def remove_guild_member(self, guild_id: int, member_id: int):
        """
        Makes an API call to remove a member from a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            member_id (int): The ID of the member.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "DELETE",
            Route(f"/guilds/{guild_id}/members/{member_id}"),
            guild_id=guild_id,
        )

    async def get_guild_bans(self, guild_id: int) -> List[Dict[str, Any]]:
        """
        Makes an API call to get the bans of a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/bans"), guild_id=guild_id
        )

    async def get_guild_ban(self, guild_id: int, user_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get the ban of a user in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            user_id (int): The ID of the user.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/bans/{user_id}"), guild_id=guild_id
        )

    async def create_guild_ban(
        self, guild_id: int, user_id: int, *, delete_message_days: int = 0
    ):
        """
        Makes an API call to ban a user in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            user_id (int): The ID of the user.
            delete_message_days (int): The number of days to delete messages for.

        Returns:
            The data returned from the API.

        """
        payload = {"delete_message_days": delete_message_days}
        return await self.request(
            "PUT",
            Route(f"/guilds/{guild_id}/bans/{user_id}", guild_id=guild_id),
            json=payload,
        )

    async def remove_guild_ban(self, guild_id: int, user_id: int):
        """
        Makes an API call to unban a user in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            user_id (int): The ID of the user.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "DELETE", Route(f"/guilds/{guild_id}/bans/{user_id}"), guild_id=guild_id
        )

    async def get_guild_roles(self, guild_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get the roles of a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/roles"), guild_id=guild_id
        )

    async def create_guild_role(
        self,
        guild_id: int,
        *,
        name: Optional[str] = None,
        permissions: Optional[int] = None,
        color: Optional[int] = None,
        hoist: bool = False,
        mentionable: bool = False,
        icon: Optional[bytes] = None,
        unicode_emoji: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create a role in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            name (Optional[str]): The name of the role.
            permissions (Optional[int]): The permissions of the role.
            color (Optional[int]): The color of the role.
            hoist (bool): Whether the role is hoisted.
            mentionable (bool): Whether the role is mentionable.
            icon (Optional[str]): The icon of the role.
            unicode_emoji (Optional[str]): The unicode emoji of the role.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {},
            name=name,
            permissions=permissions,
            color=color,
            hoist=hoist,
            mentionable=mentionable,
            icon=icon,
            unicode_emoji=unicode_emoji,
        )

        if "icon" in payload:
            payload["icon"] = bytes_to_data_uri(payload["icon"])

        return await self.request(
            "POST", Route(f"/guilds/{guild_id}/roles", guild_id=guild_id), json=payload
        )

    async def modify_guild_role(
        self,
        guild_id: int,
        role_id: int,
        *,
        name: Optional[str] = None,
        permissions: Optional[int] = None,
        color: Optional[int] = None,
        hoist: Optional[bool] = None,
        mentionable: Optional[bool] = None,
        icon: Optional[bytes] = None,
        unicode_emoji: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to modify a role in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            role_id (int): The ID of the role.
            name (Optional[str]): The name of the role.
            permissions (Optional[int]): The permissions of the role.
            color (Optional[int]): The color of the role.
            hoist (Optional[bool]): Whether the role is hoisted.
            mentionable (Optional[bool]): Whether the role is mentionable.
            icon (Optional[str]): The icon of the role.
            unicode_emoji (Optional[str]): The unicode emoji of the role.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {},
            name=name,
            permissions=permissions,
            color=color,
            hoist=hoist,
            mentionable=mentionable,
            icon=icon,
            unicode_emoji=unicode_emoji,
        )

        if "icon" in payload:
            payload["icon"] = bytes_to_data_uri(payload["icon"])

        return await self.request(
            "PATCH",
            Route(f"/guilds/{guild_id}/roles/{role_id}", guild_id=guild_id),
            json=payload,
        )

    async def delete_guild_role(self, guild_id: int, role_id: int):
        """
        Makes an API call to delete a role in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            role_id (int): The ID of the role.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "DELETE", Route(f"/guilds/{guild_id}/roles/{role_id}"), guild_id=guild_id
        )

    async def get_guild_prune_count(
        self, guild_id: int, *, days: int = 7, include_roles: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        Makes an API call to get the number of members to prune in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            days (int): The number of days to count.
            include_roles (Optional[List[int]]): The IDs of the roles to include.

        Returns:
            The data returned from the API.

        """
        payload = {"days": str(days)}
        if include_roles is not None:
            payload["include_roles"] = ",".join(map(str, include_roles))

        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/prune", guild_id=guild_id), json=payload
        )

    async def begin_guild_prune(
        self,
        guild_id: int,
        *,
        days: int = 7,
        compute_prune_count: bool = True,
        include_roles: Optional[List[int]] = None,
    ):
        """
        Makes an API call to begin pruning a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            days (int): The number of days to count.
            compute_prune_count (bool): Whether to compute the prune count.
            include_roles (Optional[List[int]]): The IDs of the roles to include.

        Returns:
            The data returned from the API.

        """
        payload = {"days": str(days), "compute_prune_count": compute_prune_count}

        if include_roles is not None:
            payload["include_roles"] = ",".join(map(str, include_roles))

        await self.request(
            "POST", Route(f"/guilds/{guild_id}/prune", guild_id=guild_id), json=payload
        )

    async def get_guild_voice_regions(self, guild_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get the voice regions in a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/regions"), guild_id=guild_id
        )

    async def get_guild_invites(self, guild_id: int) -> List[Dict[str, Any]]:
        """
        Makes an API call to get the invites in a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/invites"), guild_id=guild_id
        )

    async def get_guild_integrations(self, guild_id: int) -> List[Dict[str, Any]]:
        """
        Makes an API call to get the integrations in a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/integrations"), guild_id=guild_id
        )

    async def delete_guild_integration(self, guild_id: int, integration_id: int):
        """
        Makes an API call to delete an integration in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            integration_id (int): The ID of the integration.

        """
        return await self.request(
            "DELETE",
            Route(
                f"/guilds/{guild_id}/integrations/{integration_id}", guild_id=guild_id
            ),
        )

    async def get_guild_widget_settings(self, guild_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get the widget settings in a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/widget"), guild_id=guild_id
        )

    async def get_guild_widget(self, guild_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get the widget in a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/widget.json"), guild_id=guild_id
        )

    async def get_guild_vanity_url(self, guild_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get the vanity URL in a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/vanity-url"), guild_id=guild_id
        )

    async def get_guild_widget_image(
        self, guild_id: int, *, style: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Makes an API call to get the widget image in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            style (Optional[str]): The style of the image.

        Returns:
            The data returned from the API.

        """
        payload = {"style": style or "shield"}

        return await self.request(
            "GET",
            Route(f"/guilds/{guild_id}/widget.png", guild_id=guild_id),
            json=payload,
        )

    async def get_guild_welcome_screen(self, guild_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get the welcome screen in a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/welcome-screen"), guild_id=guild_id
        )

    async def modify_guild_welcome_screen(
        self,
        guild_id: int,
        *,
        enabled: Optional[bool] = None,
        description: Optional[str] = None,
        welcome_channels: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to modify the welcome screen in a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            enabled (Optional[bool]): Whether the welcome screen is enabled.
            description (Optional[str]): The welcome screen description.
            welcome_channels (Optional[List[int]]): The IDs of the welcome channels.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {},
            enabled=enabled,
            description=description,
            welcome_channels=welcome_channels,
        )

        return await self.request(
            "PATCH",
            Route(f"/guilds/{guild_id}/welcome-screen", guild_id=guild_id),
            json=payload,
        )

    async def get_guild_template(self, code: str) -> Dict[str, Any]:
        """
        Makes an API call to get a guild template.

        Parameters:
            code (str): The code of the template.

        Returns:
            The data returned from the API.

        """
        return await self.request("GET", Route(f"/guilds/templates/{code}"))

    async def create_guild_from_template(
        self,
        code: str,
        *,
        name: str,
        icon: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create a guild from a template.

        Parameters:
            code (str): The code of the template.
            name (str): The name of the guild.
            icon (Optional[str]): The icon of the guild.

        Returns:
            The data returned from the API.

        """
        payload = update_payload({}, name=name, icon=icon)

        if "icon" in payload:
            payload["icon"] = bytes_to_data_uri(payload["icon"])

        return await self.request(
            "POST", Route(f"/guilds/templates/{code}"), json=payload
        )

    async def get_guild_templates(self, guild_id: int) -> List[Dict[str, Any]]:
        """
        Makes an API call to get the templates in a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/templates", guild_id=guild_id)
        )

    async def create_guild_template(
        self,
        guild_id: int,
        *,
        name: str,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create a template for a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            name (str): The name of the template.
            description (Optional[str]): The description of the template.

        Returns:
            The data returned from the API.

        """
        payload = update_payload({}, name=name, description=description)

        return await self.request(
            "POST",
            Route(f"/guilds/{guild_id}/templates", guild_id=guild_id),
            json=payload,
        )

    async def sync_guild_template(self, guild_id: int, code: str) -> Dict[str, Any]:
        """
        Makes an API call to sync a template for a guild guild.

        Parameters:
            guild_id (int): The ID of the guild.
            code (str): The code of the template.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "POST",
            Route(f"/guilds/{guild_id}/templates/{code}/sync", guild_id=guild_id),
        )

    async def modify_guild_template(
        self,
        guild_id: int,
        code: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to modify a template for a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            code (str): The code of the template.
            name (Optional[str]): The name of the template.
            description (Optional[str]): The description of the template.

        Returns:
            The data returned from the API.

        """
        payload = update_payload({}, name=name, description=description)

        return await self.request(
            "PATCH",
            Route(f"/guilds/{guild_id}/templates/{code}", guild_id=guild_id),
            json=payload,
        )

    async def delete_guild_template(self, guild_id: int, code: str) -> Dict[str, Any]:
        """
        Makes an API call to delete a template for a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            code (str): The code of the template.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "DELETE", Route(f"/guilds/{guild_id}/templates/{code}", guild_id=guild_id)
        )

    async def get_invite(
        self, code: str, *, with_counts: bool = False, with_expiration: bool = False
    ) -> Dict[str, Any]:
        """
        Makes an API call to get an invite.

        Parameters:
            code (str): The code of the invite.
            with_counts (bool): Whether to include the invite counts.
            with_expiration (bool): Whether to include the invite expiration.

        Returns:
            The data returned from the API.

        """
        params = {"with_counts": with_counts, "with_expiration": with_expiration}

        return await self.request("GET", Route(f"/invites/{code}"), params=params)

    async def delete_invite(self, code: str) -> Dict[str, Any]:
        """
        Makes an API call to delete an invite.

        Parameters:
            code (str): The code of the invite.

        Returns:
            The data returned from the API.

        """
        return await self.request("DELETE", Route(f"/invites/{code}"))

    async def create_stage_instance(
        self, *, channel_id: int, topic: str, privacy_level: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Makes an API call to create a stage instance.

        Parameters:
            channel_id (int): The ID of the channel.
            topic (str): The topic of the stage instance.
            privacy_level (Optional[int]): The privacy level of the stage instance.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {}, channel_id=channel_id, topic=topic, privacy_level=privacy_level
        )

        return await self.request(
            "POST", Route("/stage-instances", channel_id=channel_id), json=payload
        )

    async def get_stage_instance(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a stage instance.

        Parameters:
            channel_id (int): The ID of the channel.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/stage-instances/{channel_id}", channel_id=channel_id)
        )

    async def modify_stage_instance(
        self,
        channel_id: int,
        *,
        topic: Optional[str] = None,
        privacy_level: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to modify a stage instance.

        Parameters:
            channel_id (int): The ID of the channel.
            topic (Optional[str]): The topic of the stage instance.
            privacy_level (Optional[int]): The privacy level of the stage instance.

        Returns:
            The data returned from the API.

        """
        payload = update_payload({}, topic=topic, privacy_level=privacy_level)

        return await self.request(
            "PATCH",
            Route(f"/stage-instances/{channel_id}", channel_id=channel_id),
            json=payload,
        )

    async def delete_stage_instance(self, channel_id: int) -> Dict[str, Any]:
        """
        Makes an API call to delete a stage instance.

        Parameters:
            channel_id (int): The ID of the channel.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "DELETE", Route(f"/stage-instances/{channel_id}"), channel_id=channel_id
        )

    async def get_sticker(self, sticker_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a sticker.

        Parameters:
            sticker_id (int): The ID of the sticker.

        Returns:
            The data returned from the API.

        """
        return await self.request("GET", Route(f"/stickers/{sticker_id}"))

    async def list_nitro_sticker_packs(self) -> Dict[str, Any]:
        """
        Makes an API call to list nitro sticker packs.

        Returns:
            The data returned from the API.

        """
        return await self.request("GET", Route("/sticker-packs"))

    async def list_guild_stickers(self, guild_id: int) -> Dict[str, Any]:
        """
        Makes an API call to list stickers for a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/stickers", guild_id=guild_id)
        )

    async def get_guild_sticker(self, guild_id: int, sticker_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a sticker for a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            sticker_id (int): The ID of the sticker.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/stickers/{sticker_id}", guild_id=guild_id)
        )

    async def modify_guild_sticker(
        self,
        guild_id: int,
        sticker_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to modify a sticker for a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            sticker_id (int): The ID of the sticker.
            name (Optional[str]): The name of the sticker.
            description (Optional[str]): The description of the sticker.
            tags (Optional[str]): The tags of the sticker.

        Returns:
            The data returned from the API.

        """
        payload = update_payload({}, name=name, description=description, tags=tags)

        return await self.request(
            "PATCH",
            Route(f"/guilds/{guild_id}/stickers/{sticker_id}", guild_id=guild_id),
            json=payload,
        )

    async def delete_guild_sticker(
        self, guild_id: int, sticker_id: int
    ) -> Dict[str, Any]:
        """
        Makes an API call to delete a sticker for a guild.

        Parameters:
            guild_id (int): The ID of the guild.
            sticker_id (int): The ID of the sticker.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "DELETE",
            Route(f"/guilds/{guild_id}/stickers/{sticker_id}", guild_id=guild_id),
        )

    async def get_current_user(self) -> Dict[str, Any]:
        """
        Makes an API call to get the current user.

        Returns:
            The data returned from the API.

        """
        return await self.request("GET", Route("/users/@me"))

    async def modify_current_user(
        self, *, username: Optional[str] = None, avatar: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """
        Makes an API call to modify the current user.

        Parameters:
            username (Optional[str]): The username of the user.
            avatar (Optional[str]): The avatar of the user.

        Returns:
            The data returned from the API.

        """
        payload = update_payload({}, username=username, avatar=avatar)

        if "avatar" in payload:
            payload["avatar"] = bytes_to_data_uri(payload["avatar"])

        return await self.request("PATCH", Route("/users/@me"), json=payload)

    async def get_current_user_guilds(self) -> List[Dict[str, Any]]:
        """
        Makes an API call to get the current user's guilds.

        Returns:
            The data returned from the API.

        """
        return await self.request("GET", Route("/users/@me/guilds"))

    async def leave_guild(self, guild_id: int):
        """
        Makes an API call to leave a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        """
        await self.request(
            "DELETE", Route(f"/users/@me/guilds/{guild_id}", guild_id=guild_id)
        )

    async def create_dm_channel(self, recipient_id: int) -> Dict[str, Any]:
        """
        Makes an API call which creates a DM channel to a user.

        Parameters:
            recipient_id (int): The ID of the user which to open the DM channel to.

        Returns:
            The data received from the API after making the call.

        """
        payload = {"recipient_id": recipient_id}
        return await self.request("POST", Route("/users/@me/channels"), json=payload)

    async def list_voice_regions(self) -> List[Dict[str, Any]]:
        """
        Makes an API call to list voice regions.

        Returns:
            The data returned from the API.

        """
        return await self.request("GET", Route("/voice/regions"))

    async def create_webhook(
        self,
        channel_id: int,
        *,
        name: str,
        avatar: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create a webhook.

        Parameters:
            channel_id (int): The ID of the channel to create the webhook in.
            name (str): The name of the webhook.
            avatar (Optional[bytes]): The avatar of the webhook.

        Returns:
            The data returned from the API.

        """
        payload = {
            "name": name,
            "avatar": bytes_to_data_uri(avatar) if avatar else None,
        }

        return await self.request(
            "POST",
            Route(f"/channels/{channel_id}/webhooks", channel_id=channel_id),
            json=payload,
        )

    async def get_channel_webhooks(self, channel_id: int) -> List[Dict[str, Any]]:
        """
        Makes an API call to get the webhooks for a channel.

        Parameters:
            channel_id (int): The ID of the channel.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/channels/{channel_id}/webhooks", channel_id=channel_id)
        )

    async def get_guild_webhooks(self, guild_id: int) -> List[Dict[str, Any]]:
        """
        Makes an API call to get the webhooks for a guild.

        Parameters:
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/webhooks", guild_id=guild_id)
        )

    async def get_webhook(self, webhook_id: int) -> Dict[str, Any]:
        """
        Makes an API call to get a webhook.

        Parameters:
            webhook_id (int): The ID of the webhook.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/webhooks/{webhook_id}", webhook_id=webhook_id)
        )

    async def get_webhook_with_token(
        self, webhook_id: int, webhook_token: str
    ) -> Dict[str, Any]:
        """
        Makes an API call to get a webhook with a token.

        Parameters:
            webhook_id (int): The ID of the webhook.
            webhook_token (str): The token of the webhook.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET",
            Route(
                f"/webhooks/{webhook_id}/{webhook_token}",
                webhook_id=webhook_id,
                webhookd_token=webhook_token,
            ),
        )

    async def modify_webhook(
        self,
        webhook_id: int,
        *,
        name: Optional[str] = None,
        avatar: Optional[bytes] = None,
        channel_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to modify a webhook.

        Parameters:
            webhook_id (int): The ID of the webhook.
            name (Optional[str]): The name of the webhook.
            avatar (Optional[bytes]): The avatar of the webhook.
            channel_id (Optional[int]): The ID of the channel to move the webhook to.

        Returns:
            The data returned from the API.

        """
        payload = update_payload({}, name=name, avatar=avatar, channel_id=channel_id)

        if "avatar" in payload:
            payload["avatar"] = bytes_to_data_uri(payload["avatar"])

        return await self.request(
            "PATCH",
            Route(f"/webhooks/{webhook_id}", webhook_id=webhook_id),
            json=payload,
        )

    async def modify_webhook_with_token(
        self,
        webhook_id: int,
        webhook_token: str,
        *,
        name: Optional[str] = None,
        avatar: Optional[bytes] = None,
    ):
        """
        Makes an API call to modify a webhook with a token.

        Parameters:
            webhook_id (int): The ID of the webhook.
            webhook_token (str): The token of the webhook.
            name (Optional[str]): The name of the webhook.
            avatar (Optional[bytes]): The avatar of the webhook.

        """
        payload = update_payload(
            {},
            name=name,
            avatar=avatar,
        )

        if "avatar" in payload:
            payload["avatar"] = bytes_to_data_uri(payload["avatar"])

        await self.request(
            "PATCH",
            Route(
                f"/webhooks/{webhook_id}/{webhook_token}",
                webhook_id=webhook_id,
                webhook_token=webhook_token,
            ),
            json=payload,
        )

    async def delete_webhook(self, webhook_id: int) -> None:
        """
        Makes an API call to delete a webhook.

        Parameters:
            webhook_id (int): The ID of the webhook.

        """
        await self.request(
            "DELETE", Route(f"/webhooks/{webhook_id}", webhook_id=webhook_id)
        )

    async def delete_webhook_with_token(
        self, webhook_id: int, webhook_token: str
    ) -> None:
        """
        Makes an API call to delete a webhook with a token.

        Parameters:
            webhook_id (int): The ID of the webhook.
            webhook_token (str): The token of the webhook.

        """
        await self.request(
            "DELETE",
            Route(
                f"/webhooks/{webhook_id}/{webhook_token}",
                webhook_id=webhook_id,
                webhook_token=webhook_token,
            ),
        )

    async def execute_webhook(
        self,
        webhook_id: int,
        webhook_token: str,
        *,
        content: Optional[str] = None,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        tts: Optional[bool] = None,
        file: Optional[io.BufferedIOBase] = None,
        embeds: Optional[List[Dict[str, Any]]] = None,
        allowed_mentions: Optional[Dict[str, Any]] = None,
        componenets: Optional[List[Dict[str, Any]]] = None,
        wait: Optional[bool] = None,
        thread_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to execute a webhook.

        Parameters:
            webhook_id (int): The ID of the webhook.
            webhook_token (str): The token of the webhook.
            content (Optional[str]): The content of the message.
            username (Optional[str]): The username of the webhook.
            avatar_url (Optional[str]): The avatar url of the webhook.
            tts (Optional[bool]): Whether the message should be TTS.
            file (Optional[io.BufferedIOBase]): The file to upload.
            embeds (Optional[List[Dict[str, Any]]]): The embeds to send.
            allowed_mentions (Optional[Dict[str, Any]]): The allowed mentions.
            componenets (Optional[List[Dict[str, Any]]]): The components to send.
            wait (Optional[bool]): Whether to wait for server confirmation  before response.
            thread_id (Optional[int]): The ID of the thread to post to.

        Returns:
            The data returned from the API.

        """
        form = []
        payload = update_payload(
            {},
            content=content,
            username=username,
            avatar_url=avatar_url,
            tts=tts,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            componenets=componenets,
        )

        params = update_payload({}, wait=wait, thread_id=thread_id)

        if file:
            form.append(
                {
                    "name": "file",
                    "value": file,
                    "filename": getattr(file, "name", None),
                    "content_type": "application/octect-stream",
                }
            )

        return await self.request(
            "POST",
            Route(
                f"/webhooks/{webhook_id}/{webhook_token}",
                webhook_id=webhook_id,
                webhook_token=webhook_token,
            ),
            json=payload,
            form=form,
            params=params,
        )

    async def get_webhook_message(
        self, webhook_id: int, webhook_token: str, message_id: int
    ) -> Dict[str, Any]:
        """
        Makes an API call to get a webhook message.

        Parameters:
            webhook_id (int): The ID of the webhook.
            webhook_token (str): The token of the webhook.
            message_id (int): The ID of the message.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET",
            Route(
                f"/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}",
                webhook_id=webhook_id,
                webhook_token=webhook_token,
            ),
        )

    async def edit_webhook_message(
        self,
        webhook_id: int,
        webhook_token: str,
        message_id: int,
        *,
        content: Optional[str] = None,
        embeds: Optional[List[Dict[str, Any]]] = None,
        file: Optional[io.BufferedIOBase] = None,
        allowed_mentions: Optional[Dict[str, Any]] = None,
        componenets: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to edit a webhook message.

        Parameters:
            webhook_id (int): The ID of the webhook.
            webhook_token (str): The token of the webhook.
            message_id (int): The ID of the message.
            content (Optional[str]): The content of the message.
            embeds (Optional[List[Dict[str, Any]]]): The embeds to send.
            file (Optional[io.BufferedIOBase]): The file to upload.
            allowed_mentions (Optional[Dict[str, Any]]): The allowed mentions.
            componenets (Optional[List[Dict[str, Any]]]): The components to send.
            attachments (Optional[List[Dict[str, Any]]]): The attachments to send.

        Returns:
            The data returned from the API.

        """
        form = []
        payload = update_payload(
            {},
            content=content,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            componenets=componenets,
            attachments=attachments,
        )

        if file:
            form.append(
                {
                    "name": "file",
                    "value": file,
                    "filename": getattr(file, "name", None),
                    "content_type": "application/octect-stream",
                }
            )

        return await self.request(
            "PATCH",
            Route(
                f"/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}",
                webhook_id=webhook_id,
                webhook_token=webhook_token,
            ),
            json=payload,
            form=form,
        )

    async def delete_webhook_message(
        self, webhook_id: int, webhook_token: str, message_id: int
    ):
        """
        Makes an API call to delete a webhook message.

        Parameters:
            webhook_id (int): The ID of the webhook.
            webhook_token (str): The token of the webhook.
            message_id (int): The ID of the message.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "DELETE",
            Route(
                f"/webhooks/{webhook_id}/{webhook_token}/messages/{message_id}",
                webhook_id=webhook_id,
                webhook_token=webhook_token,
            ),
        )

    async def get_global_application_commands(
        self, application_id: int
    ) -> List[Dict[str, Any]]:
        """
        Makes an API call to get global application commands.

        Parameters:
            application_id (int): The ID of the application.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/applications/{application_id}/commands")
        )

    async def create_global_application_command(
        self,
        application_id: int,
        *,
        name: str,
        description: str,
        options: Optional[List[Dict[str, Any]]] = None,
        default_permission: bool = True,
        type: int = 1,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create a global application command.

        Parameters:
            application_id (int): The ID of the application.
            name (str): The name of the command.
            description (str): The description of the command.
            options (Optional[List[Dict[str, Any]]]): The options of the command.
            default_permission (bool): Whether the command is enabled by default.
            type (int): The type of the command.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {},
            name=name,
            description=description,
            options=options,
            default_permission=default_permission,
            type=type,
        )

        return await self.request(
            "POST", Route(f"/applications/{application_id}/commands"), json=payload
        )

    async def get_global_application_command(
        self, application_id: int, command_id: int
    ) -> Dict[str, Any]:
        """
        Makes an API call to get a global application command.

        Parameters:
            application_id (int): The ID of the application.
            command_id (int): The ID of the command.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET", Route(f"/applications/{application_id}/commands/{command_id}")
        )

    async def edit_global_application_command(
        self,
        application_id: int,
        command_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        options: Optional[List[Dict[str, Any]]] = None,
        default_permission: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to edit a global application command.

        Parameters:
            application_id (int): The ID of the application.
            command_id (int): The ID of the command.
            name (Optional[str]): The name of the command.
            description (Optional[str]): The description of the command.
            options (Optional[List[Dict[str, Any]]]): The options of the command.
            default_permission (Optional[bool]): Whether the command is enabled by default.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {},
            name=name,
            description=description,
            options=options,
            default_permission=default_permission,
        )

        return await self.request(
            "PATCH",
            Route(f"/applications/{application_id}/commands/{command_id}"),
            json=payload,
        )

    async def delete_global_application_command(
        self, application_id: int, command_id: int
    ) -> None:
        """
        Makes an API call to delete a global application command.

        Parameters:
            application_id (int): The ID of the application.
            command_id (int): The ID of the command.

        """
        await self.request(
            "DELETE", Route(f"/applications/{application_id}/commands/{command_id}")
        )

    async def bulk_overwrite_global_application_commands(
        self, application_id: int, *, commands: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Makes an API call to bulk overwrite global application commands.

        Parameters:
            application_id (int): The ID of the application.
            commands (List[Dict[str, Any]]): The commands to overwrite.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "PUT", Route(f"/applications/{application_id}/commands"), json=commands
        )

    async def get_guild_application_commands(
        self, application_id: int, guild_id: int
    ) -> List[Dict[str, Any]]:
        """
        Makes an API call to get guild application commands.

        Parameters:
            application_id (int): The ID of the application.
            guild_id (int): The ID of the guild.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET",
            Route(
                f"/applications/{application_id}/guilds/{guild_id}/commands",
                guild_id=guild_id,
            ),
        )

    async def create_guild_application_command(
        self,
        application_id: int,
        guild_id: int,
        *,
        name: str,
        description: str,
        options: Optional[List[Dict[str, Any]]] = None,
        default_permission: bool = True,
        type: int = 1,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create a guild application command.

        Parameters:
            application_id (int): The ID of the application.
            name (str): The name of the command.
            description (str): The description of the command.
            options (Optional[List[Dict[str, Any]]]): The options of the command.
            default_permission (bool): Whether the command is enabled by default.
            type (int): The type of the command.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {},
            name=name,
            description=description,
            options=options,
            default_permission=default_permission,
            type=type,
        )

        return await self.request(
            "POST",
            Route(
                f"/applications/{application_id}/guilds/{guild_id}/commands",
                guild_id=guild_id,
            ),
            json=payload,
        )

    async def get_guild_application_command(
        self, application_id: int, guild_id: int, command_id: int
    ) -> Dict[str, Any]:
        """
        Makes an API call to get a guild application command.

        Parameters:
            application_id (int): The ID of the application.
            guild_id (int): The ID of the guild.
            command_id (int): The ID of the command.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET",
            Route(
                f"/applications/{application_id}/guilds/{guild_id}/commands/{command_id}",
                guild_id=guild_id,
            ),
        )

    async def edit_guild_application_command(
        self,
        application_id: int,
        guild_id: int,
        command_id: int,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        options: Optional[List[Dict[str, Any]]] = None,
        default_permission: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to edit a guild application command.

        Parameters:
            application_id (int): The ID of the application.
            guild_id (int): The ID of the guild.
            command_id (int): The ID of the command.
            name (Optional[str]): The name of the command.
            description (Optional[str]): The description of the command.
            options (Optional[List[Dict[str, Any]]]): The options of the command.
            default_permission (Optional[bool]): Whether the command is enabled by default.

        Returns:
            The data returned from the API.

        """
        payload = update_payload(
            {},
            name=name,
            description=description,
            options=options,
            default_permission=default_permission,
        )

        return await self.request(
            "PATCH",
            Route(
                f"/applications/{application_id}/guilds/{guild_id}/commands/{command_id}",
                guild_id=guild_id,
            ),
            json=payload,
        )

    async def delete_guild_application_command(
        self, application_id: int, guild_id: int, command_id: int
    ):
        """
        Makes an API call to delete a guild application command.

        Parameters:
            application_id (int): The ID of the application.
            guild_id (int): The ID of the guild.
            command_id (int): The ID of the command.

        """
        await self.request(
            "DELETE",
            Route(
                f"/applications/{application_id}/guilds/{guild_id}/commands/{command_id}",
                guild_id=guild_id,
            ),
        )

    async def bulk_overwrite_guild_application_commands(
        self, application_id: int, guild_id: int, *, commands: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Makes an API call to bulk overwrite guild application commands.

        Parameters:
            application_id (int): The ID of the application.
            guild_id (int): The ID of the guild.
            commands (List[Dict[str, Any]]): The commands to overwrite.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "PUT",
            Route(
                f"/applications/{application_id}/guilds/{guild_id}/commands",
                guild_id=guild_id,
            ),
            json=commands,
        )

    async def get_guild_application_command_permissions(
        self, application_id: int, guild_id: int
    ) -> List[Dict[str, Any]]:
        """
        Makes an API call to get guild application command permissions.

        Parameters:
            application_id (int): The ID of the application.
            guild_id (int): The ID of the guild.
            command_id (int): The ID of the command.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET",
            Route(
                f"/applications/{application_id}/guilds/{guild_id}/commands/permissions",
                guild_id=guild_id,
            ),
        )

    async def get_application_command_permissions(
        self, application_id: int, guild_id: int, command_id: int
    ) -> Dict[str, Any]:
        """
        Makes an API call to get application command permissions.

        Parameters:
            application_id (int): The ID of the application.
            guild_id (int): The ID of the guild.
            command_id (int): The ID of the command.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET",
            Route(
                f"/applications/{application_id}/guilds/{guild_id}/commands/{command_id}/permissions",
                guild_id=guild_id,
            ),
        )

    async def edit_application_command_permissions(
        self,
        application_id: int,
        guild_id: int,
        command_id: int,
        *,
        permissions: List[Dict[str, Any]],
    ):
        """
        Makes an API call to edit application command permissions.

        Parameters:
            application_id (int): The ID of the application.
            guild_id (int): The ID of the guild.
            command_id (int): The ID of the command.
            permissions (List[Dict[str, Any]]): The permissions to edit.

        Returns:
            The data returned from the API.

        """
        payload = {"permissions": permissions}
        return await self.request(
            "PATCH",
            Route(
                f"/applications/{application_id}/guilds/{guild_id}/commands/{command_id}/permissions",
                guild_id=guild_id,
            ),
            json=payload,
        )

    async def batch_edit_application_command_permissions(
        self, application_id: int, guild_id: int, *, permissions: List[Dict[str, Any]]
    ):
        """
        Makes an API call to batch edit application command permissions.

        Parameters:
            application_id (int): The ID of the application.
            guild_id (int): The ID of the guild.
            permissions (List[Dict[str, Any]]): The permissions to edit.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "PATCH",
            Route(
                f"/applications/{application_id}/guilds/{guild_id}/commands/permissions",
                guild_id=guild_id,
            ),
            json=permissions,
        )

    async def create_interaction_response(
        self,
        interaction_id: int,
        interaction_token: str,
        *,
        type: int,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create an interaction response.

        Parameters:
            interaction_id (int): The ID of the interaction.
            interaction_token (str): The token of the interaction.
            type (int): The type of the response.
            data (Optional[Dict[str, Any]]): The data of the response.

        Returns:
            The data returned from the API.

        """
        payload = update_payload({}, type=type, data=data)
        return await self.request(
            "POST",
            Route(f"/interactions/{interaction_id}/{interaction_token}/callback"),
            json=payload,
        )

    async def get_original_interaction_response(
        self, application_id: int, interaction_token: str
    ) -> Dict[str, Any]:
        """
        Makes an API call to get the original interaction response.

        Parameters:
            application_id (int): The ID of the application.
            interaction_token (str): The token of the interaction.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET",
            Route(f"/webhooks/{application_id}/{interaction_token}/messages/@original"),
        )

    async def edit_original_interaction_response(
        self,
        application_id: int,
        interaction_token: str,
        *,
        content: Optional[str] = None,
        embeds: Optional[List[Dict[str, Any]]] = None,
        file: Optional[io.BufferedIOBase] = None,
        allowed_mentions: Optional[Dict[str, Any]] = None,
        componenets: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to edit the original interaction response.

        Parameters:
            application_id (int): The ID of the application.
            interaction_token (str): The token of the interaction.
            content (Optional[str]): The content of the response.
            embeds (Optional[List[Dict[str, Any]]]): The embeds of the response.
            file (Optional[io.BufferedIOBase]): The file of the response.
            allowed_mentions (Optional[Dict[str, Any]]): The allowed mentions of the response.
            componenets (Optional[List[Dict[str, Any]]]): The components of the response.
            attachments (Optional[List[Dict[str, Any]]]): The attachments of the response.

        Returns:
            The data returned from the API.

        """
        form = []
        payload = update_payload(
            {},
            content=content,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            componenets=componenets,
            attachments=attachments,
        )

        if file:
            form.append(
                {
                    "name": "file",
                    "value": file,
                    "filename": getattr(file, "name", None),
                    "content_type": "application/octect-stream",
                }
            )

        return await self.request(
            "PATCH",
            Route(f"/webhooks/{application_id}/{interaction_token}/messages/@original"),
            json=payload,
            form=form,
        )

    async def delete_original_interaction_response(
        self, application_id: int, interaction_token: str
    ):
        """
        Makes an API call to delete the original interaction response.

        Parameters:
            application_id (int): The ID of the application.
            interaction_token (str): The token of the interaction.

        Returns:
            The data returned from the API.

        """
        await self.request(
            "DELETE",
            Route(f"/webhooks/{application_id}/{interaction_token}/messages/@original"),
        )

    async def create_followup_message(
        self,
        application_id: int,
        interaction_token: str,
        *,
        content: Optional[str] = None,
        embeds: Optional[List[Dict[str, Any]]] = None,
        file: Optional[io.BufferedIOBase] = None,
        allowed_mentions: Optional[Dict[str, Any]] = None,
        componenets: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        flags: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to create a followup message.

        Parameters:
            application_id (int): The ID of the application.
            interaction_token (str): The token of the interaction.
            content (Optional[str]): The content of the response.
            embeds (Optional[List[Dict[str, Any]]]): The embeds of the response.
            file (Optional[io.BufferedIOBase]): The file of the response.
            allowed_mentions (Optional[Dict[str, Any]]): The allowed mentions of the response.
            componenets (Optional[List[Dict[str, Any]]]): The components of the response.
            attachments (Optional[List[Dict[str, Any]]]): The attachments of the response.
            flags (Optional[int]): The flags of the response.

        Returns:
            The data returned from the API.

        """
        form = []
        payload = update_payload(
            {},
            content=content,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            componenets=componenets,
            attachments=attachments,
            flags=flags,
        )

        if file:
            form.append(
                {
                    "name": "file",
                    "value": file,
                    "filename": getattr(file, "name", None),
                    "content_type": "application/octect-stream",
                }
            )

        return await self.request(
            "POST",
            Route(f"/webhooks/{application_id}/{interaction_token}/messages"),
            json=payload,
            form=form,
        )

    async def get_followup_message(
        self, application_id: int, interaction_token: str, message_id: int
    ) -> Dict[str, Any]:
        """
        Makes an API call to get a followup message.

        Parameters:
            application_id (int): The ID of the application.
            interaction_token (str): The token of the interaction.
            message_id (int): The ID of the message.

        Returns:
            The data returned from the API.

        """
        return await self.request(
            "GET",
            Route(
                f"/webhooks/{application_id}/{interaction_token}/messages/{message_id}"
            ),
        )

    async def edit_followup_message(
        self,
        application_id: int,
        interaction_token: str,
        message_id: int,
        *,
        content: Optional[str] = None,
        embeds: Optional[List[Dict[str, Any]]] = None,
        file: Optional[io.BufferedIOBase] = None,
        allowed_mentions: Optional[Dict[str, Any]] = None,
        componenets: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Makes an API call to edit a followup message.

        Parameters:
            application_id (int): The ID of the application.
            interaction_token (str): The token of the interaction.
            message_id (int): The ID of the message.
            content (Optional[str]): The content of the response.
            embeds (Optional[List[Dict[str, Any]]]): The embeds of the response.
            file (Optional[io.BufferedIOBase]): The file of the response.
            allowed_mentions (Optional[Dict[str, Any]]): The allowed mentions of the response.
            componenets (Optional[List[Dict[str, Any]]]): The components of the response.
            attachments (Optional[List[Dict[str, Any]]]): The attachments of the response.

        Returns:
            The data returned from the API.

        """
        form = []
        payload = update_payload(
            {},
            content=content,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            componenets=componenets,
            attachments=attachments,
        )

        if file:
            form.append(
                {
                    "name": "file",
                    "value": file,
                    "filename": getattr(file, "name", None),
                    "content_type": "application/octect-stream",
                }
            )

        return await self.request(
            "PATCH",
            Route(
                f"/webhooks/{application_id}/{interaction_token}/messages/{message_id}"
            ),
            json=payload,
            form=form,
        )

    async def delete_followup_message(
        self, application_id: int, interaction_token: str, message_id: int
    ):
        """
        Makes an API call to delete a followup message.

        Parameters:
            application_id (int): The ID of the application.
            interaction_token (str): The token of the interaction.
            message_id (int): The ID of the message.

        """
        await self.request(
            "DELETE",
            Route(
                f"/webhooks/{application_id}/{interaction_token}/messages/{message_id}"
            ),
        )

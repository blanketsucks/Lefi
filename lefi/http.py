from __future__ import annotations

import asyncio
import aiohttp

import logging
import json

from typing import Any, ClassVar, Dict, List, Optional, Union

from .errors import BadRequest, Forbidden, NotFound, Unauthorized
from .ratelimiter import Ratelimiter
from .utils import bytes_to_data_uri, update_payload
from .objects import File

__all__ = (
    "HTTPClient",
    "Route",
)

logger = logging.getLogger(__name__)

BASE: str = "https://discord.com/api/v9"


class Route:
    """A class representing an endpoint.

    This class is used to handle ratelimit buckets. The kwargs passed
    to this class should be for the major parameters of the endpoint.
    This is used to make a "bucket" which is later used in the ratelimiter.

    Parameters
    ----------
    path: :class:`str`
        The path of the endpoint

    **kwargs: Any
        Major parameters to pass for the endpoint

    Attributes
    ----------
    params: :class:`dict`
        The kwargs passed to the constructor

    path: :class:`str`
        The endpoint path.

    channel_id: Optional[:class:`int`]
        The channel_id being used in the endpoint if there is any

    guild_id: Optional[:class:`int`]
        The guild_id being used in the endpoint if there is any

    webhook_id: Optional[:class:`int`]
        The webhook_id being used in the endpoint if there is any

    webhook_token: Optional[:class:`str`]
        The webhook_token being used in the endpoint if there is any

    lock: :class:`asyncio.Lock`
        The internal lock to use for ratelimiting. This is acquired when
        the bucket is depleted.
    """

    def __init__(self, path: str, **kwargs) -> None:
        self.params: dict = kwargs
        self.path: str = path

        self.channel_id: Optional[int] = kwargs.get("channel_id")
        self.guild_id: Optional[int] = kwargs.get("guild_id")
        self.webhook_id: Optional[int] = kwargs.get("webhook_id")
        self.webhook_token: Optional[str] = kwargs.get("webhookd_token")

        self.lock: asyncio.Lock = asyncio.Lock()

    @property
    def url(self) -> str:
        """The final url of the route."""
        return f"{BASE+self.path}"

    @property
    def bucket(self) -> str:
        """The bucket of the route."""
        return f"{self.channel_id}:{self.guild_id}:{self.webhook_id}:{self.path}"


class HTTPClient:
    """A class used to handle API calling and ratelimits to the API.

    .. warning ::

        This class is only used internally, this should not and is not
        meant to be called on directly.

    Parameters
    ----------
    token: :class:`str`
        The token to use for authorization
    loop: :class:`asyncio.AbstractEventLoop`
        The loop to use

    Attributes
    ----------
    token: :class:`str`
        The token to use for authorization

    loop: :class:`asyncio.AbstractEventLoop`
        The loop to use

    session: :class:`aiohttp.ClientSession`
        The client session to use for making requests

    semaphores: Dict[str, :class:`asyncio.Semaphore`]
        A mapping of buckets and semaphores. This is used for
        concurrent requests without getting ratelimited.
    """

    ERRORS: ClassVar[Dict[int, Any]] = {
        400: BadRequest,
        401: Unauthorized,
        403: Forbidden,
        404: NotFound,
    }

    def __init__(self, token: str, loop: asyncio.AbstractEventLoop) -> None:
        self.token: str = token
        self.loop: asyncio.AbstractEventLoop = loop
        self.session: aiohttp.ClientSession = None  # type: ignore
        self.semaphores: Dict[str, asyncio.Semaphore] = {}

    @staticmethod
    async def json_or_text(resp: aiohttp.ClientResponse) -> Union[dict, str]:
        """A method which returns a response's text or json.

        This is a utility method, to return a :class:`aiohttp.ClientResponse`'s
        text or json.

        Parameters
        ----------
        resp: :class:`aiohttp.ClientResponse`
            The client response returned from a request.

        Returns
        -------
        Union[:class:`dict`, :class:`str`]
            The data/text returned from :meth:`aiohttp.ClientResponse.json` or
            :meth:`aiohttp.ClientResponse.text`
        """
        try:
            return await resp.json()
        except aiohttp.ContentTypeError:
            return await resp.text()

    async def _create_session(
        self, loop: asyncio.AbstractEventLoop = None
    ) -> aiohttp.ClientSession:
        """A method which creates the internal :class:`aiohttp.ClientSession`

        This method is used to create the internal :class:`aiohttp.ClientSession` that
        is used for making every API call currently supported.

        Parameters
        ----------
        loop: :class:`asyncio.AbstractEventLoop`
            The loop to use for the client session

        Returns
        -------
        :class:`aiohttp.ClientSession`
            The created client session.
        """
        return aiohttp.ClientSession(loop=self.loop or loop)

    async def close(self) -> None:
        """A method which closes the internal :class:`aiohttp.ClientSession`"""
        await self.session.close()

    async def request(self, method: str, route: Route, **kwargs) -> Any:
        """A method which is used to make requests to the API.

        This method is used to make API calls internally throughout the wrapper.
        This method calls upon the ratelimiter to ensure that the client will not get ratelimited
        as easily.

        Parameters
        ----------
        method: :class:`str`
            The method to request with. E.g `POST` and `GET`

        route: :class:`.Route`
            The route to make a request from

        **kwargs: Any
            Extra kwargs to pass when making the request. E.g `json = ...`

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request

        Returns
        -------
        Any
            The return data of the request
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

    async def get_bot_gateway(self) -> dict:
        """A method which makes an API call to get bot's gateway.

        This method is used to make an API call to the get the bot's gateway information.
        This is used for getting information such as, how many shards the bot should use and
        The max concurrency.

        This calls the ``/gateway/bot`` endpoint.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong during the request

        Returns
        -------
        :class:`dict`
            The return data from the request.
        """
        return await self.request("GET", Route("/gateway/bot"))

    async def ws_connect(self, url: str) -> aiohttp.ClientWebSocketResponse:
        """A method which is used to connect to the websocket.

        This method connects to the gateway/websocket url. This is used to create the
        internal websocket for all of the websocket clients in this wrapper.

        Parameters
        ----------
        url: :class:`str`
            The websocket/gateway url to connect to

        Returns
        -------
        :class:`aiohttp.ClientWebSocketResponse`
            The websocket after connection is established.
        """
        return await self.session.ws_connect(url)

    async def read_from_url(self, url: str) -> bytes:
        """A method to read the data from a url.

        This method is mostly here as a utility method, used in some places.

        Parameters
        ----------
        url: :class:`str`
            The url to read the data from

        Raises
        ------
        :exc:`aiohttp.ClientResponseError`
            Raised when the url cannot be read.

        Returns
        -------
        :class:`bytes`
            The data read from the url.
        """
        async with self.session.get(url) as resp:
            return await resp.read()

    async def login(self) -> None:
        """A method which is used to validate the token.

        This method is used to simulate logging in. It's used to check
        if the authorization token is valid by requesting ``/users/@me``

        Raises
        ------
        :exc:`.Unauthorized`
            The token is not valid.
        """
        try:
            await self.get_current_user()
        except (Forbidden, Unauthorized):
            raise Unauthorized("Invalid token")

    def build_file_form(self, file: File, index: Optional[int] = None) -> dict:
        """A method which builds a form.

        This method builds a form which is used for file uploads.

        Parameters
        ----------
        file: :class:`.File`
            The file to upload

        index: Optional[:class:`int`]
            The index of the file

        Returns
        -------
        :class:`dict`
            A dict representing the form.

        """
        return {
            "name": f"file-{index}" if index else "file",
            "value": file,
            "filename": file.filename,
            "content_type": "application/octect-stream",
        }

    def form_helper(self, files: Optional[List[Optional[File]]] = None) -> List[dict]:
        """A helper method which formats the files to be sent.

        This helper method is used to send files in a multipart/form-data request

        Parameters
        ----------
        files: Optional[Optional[List[:class:`.File`]]]
            A list of :class:`.File`'s to format

        Returns
        -------
        List[:class:`dict`]
            A list of formatted forms
        """
        form: List[dict] = []

        if not files:
            return form

        if len(files) == 1:
            file = files[0]

            if not file:
                return form

            form.append(self.build_file_form(file))
            return form

        for index, file in enumerate(files):
            if not file:
                continue

            param = self.build_file_form(file, index)
            form.append(param)

        return form

    async def get_channel(self, channel_id: int) -> dict:
        """A method which makes an API call to fetch a channel.

        This method makes a request to ``channels/channel_id`` to fetch
        a the channel corresponding to the passed in id.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to fetch

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong during the request.

        :exc:`.Forbidden`
            Your client doesn't have the permissions to
            fetch this channel.

        :exc:`.BadRequest`
            Somehow you messed up the payload.

        :exc:`.NotFound`
            The ID passed isn't valid.

        Returns
        -------
        :class:`dict`
            A dict representing the fetched channel.
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
        permission_overwrites: Optional[List[dict]] = None,
        default_auto_archive_duration: Optional[int] = None,
    ) -> dict:
        """A method which makes an API call to edit a channel.

        This method calls ``POST channels/channel_id`` to edit the channel
        This is used internally in some places such as :meth:`.TextChannel.edit`

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to edit

        name: Optional[:class:`str`]
            The new name to give the channel

        type: Optional[:class:`int`]
            The new type to give the channel

        position: Optional[:class:`int`]
            The new position of the channel

        topic: Optional[:class:`str`]
            The new topic of the channel

        nsfw: Optional[:class:`bool`]
            Whether or not the channel should be identified as NSFW

        rate_limit_per_user: Optional[:class:`int`]
            The new slowmode of the channel.

        permissions_overwrites: Optional[List[:class:`dict`]]
            A list of new permissions ovewrites for the channel

        default_auto_archive_duration: Optional[:class:`int`]
            How long in seconds it should take before a thread automatically archives itself

        Raises
        ------
        :exc:`.HTTPException`
            Something messed up when making the request.

        :exc:`.BadRequest`
            You somehow messed up the payload.

        :exc:`.Forbidden`
            You client doesn't have permissions to edit this channel.

        Returns
        -------
        :class:`dict`
            A dict representing the channel after modifying it.
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
        permission_overwrites: Optional[List[dict]] = None,
    ) -> dict:
        """A method which makes an API call to edit a channel.

        This method calls ``POST channels/channel_id`` to edit the voice channel
        This is used internally in some places such as :meth:`.VoiceChannel.edit`

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to edit

        name: Optional[:class:`str`]
            The new name to give the channel

        position: Optional[:class:`int`]
            The new position of the channel

        bitrate: Optional[:class:`int`]
            The new bitrate of the voice channel

        user_limit: Optional[:class:`int`]
            How many users to allow in the voice channel at any given time

        rtc_region: Optional[:class:`str`]
            The rtc region of the voice channel.

        video_quality_mode: Optional[:class:`int`]
            The video quality inside of the voice channel

        sync_permissions: Optional[:class:`bool`]
            Whether or not the channel should be synced to its parent's permissions

        permissions_overwrites: Optional[List[:class:`dict`]]
            A list of new permissions ovewrites for the channel

        Raises
        ------
        :exc:`.HTTPException`
            Something messed up when making the request.

        :exc:`.BadRequest`
            You somehow messed up the payload.

        :exc:`.Forbidden`
            You client doesn't have permissions to edit this channel.

        Returns
        -------
        :class:`dict`
            A dict representing the channel after modifying it.
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
            permissions_overwrites=permission_overwrites,
        )

        return await self.request(
            "PATCH",
            Route(f"/channels/{channel_id}", channel_id=channel_id),
            json=payload,
        )

    async def delete_channel(self, channel_id: int) -> None:
        """A method which makes an API call to delete a channel.

        This method calls ``DELETE /channels/channel_id`` this method
        is used internally in some places, such as :meth:`.TextChannel.delete`.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to delete

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.NotFound`
            The channel ID is invalid, or the channel was deleted already.

        :exc:`.Forbidden`
            Your client doesn't have permissions to delete this channel.
        """
        return await self.request(
            "DELETE", Route(f"/channels/{channel_id}", channel_id=channel_id)
        )

    async def get_channel_messages(
        self,
        channel_id: int,
        *,
        around: Optional[int] = None,
        before: Optional[int] = None,
        after: Optional[int] = None,
        limit: int = 50,
    ) -> List[dict]:
        """A method which makes an API call to get the channel's message history

        This method is used to fetch a list of messages in the channel specified.
        This method calls ``GET /channels/channel_id/messages``.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to get the messages from

        around: Optional[:class:`int`]
            Gets messages around this message ID

        before: Optional[:class:`int`]
            Gets messages before this message ID

        after: Optional[:class:`int`]
            Gets messages after this message ID

        limit: :class:`int`
            The max amount of messages to return

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making this request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to view this channel's history.

        Returns
        -------
        List[:class:`dict`]
            A list of dicts representing message objects.

        """
        params = {"limit": limit}

        update_payload(params, around=around, before=before, after=after)

        return await self.request(
            "GET",
            Route(f"/channels/{channel_id}/messages", channel_id=channel_id),
            params=params,
        )

    async def get_channel_message(self, channel_id: int, message_id: int) -> dict:
        """A method which makes an API call to get a message.

        This method is used to fetch a message from the API using its ID and the channel's ID.
        This is used internally in some places, such as :meth:`.TextChannel.fetch_message`

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to fetch the message from

        message_id: :class:`int`
            The id of the message to fetch

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making this request.

        :exc:`.NotFound`
            The message was not found.

        :exc:`.Forbidden`
            Your client doesn't have the permissions to fetch this message.

        Returns
        -------
        :class:`dict`
            A dict representing the fetched message.
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
        embeds: Optional[List[dict]] = None,
        allowed_mentions: Optional[dict] = None,
        message_reference: Optional[dict] = None,
        components: Optional[List[dict]] = None,
        sticker_ids: Optional[List[int]] = None,
        files: Optional[List[File]] = None,
    ) -> dict:
        """A method which makes an API call to send a message.

        This method is used to send messages. This is used in :meth:`.TextChannel.send` and
        :meth:`.DMChannel.send`.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to send the messsage in

        content: Optional[:class:`str`]
            The content of the message

        tts: :class:`bool`
            If the message should be sent with text-to-speech

        embeds: Optional[List[:class:`dict`]]
            A list of embeds to send the message with. Only 10 embeds can be sent at a time

        allowed_mentions: Optional[:class:`dict`]
            A dict representing the allowed mentions of message to send

        message_reference: Optional[:class:`dict`]
            A dict representing the message to reference

        components: Optional[List[dict]]
            A list of message components to send

        sticker_ids: Optional[List[:class:`int`]]
            A list id's of stickers to send

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making this request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to send this message.

        :exc:`.BadRequest`
            You somehow messed up the payload.

        Returns
        -------
        :class:`dict`
            A dict representing the sent message object
        """
        payload = {"tts": tts}
        form = self.form_helper(files)  # type: ignore

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

    async def crosspost_message(self, channel_id: int, message_id: int) -> dict:
        """A method which makes an API call to crosspost a message.add()

        This method makes an API call to crosspost the message in a news channel
        to following channels.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the news channel to crosspost from

        message_id: :class:`int`
            The id of the message to crosspost

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.NotFound`
            Either the channel id or the message id is invalid.

        Returns
        -------
        :class:`dict`
            A dict representing a message object.
        """
        return await self.request(
            "POST",
            Route(
                f"/channels/{channel_id}/messages/{message_id}/crosspost",
                channel_id=channel_id,
            ),
        )

    async def create_reaction(
        self, channel_id: int, message_id: int, emoji: str
    ) -> None:
        """A method which makes an API call to add a reaction.

        This method makes an API call to add a reaction to the message specified.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the message's channel

        message_id: :class:`int`
            The id of the message

        emoji: :class:`str`
            The emoji to add to the message

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.NotFound`
            Either the channel_id, message_id, or the emoji wasn't valid.

        :exc:`.Forbidden`
            Your client doesn't have permissions to add reactions to this message.
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
        """A method which makes an API call to delete a reaction.

        This method makes an API call to delete a reaction from the specified message.
        If no user_id is passed then the client will delete its own reaction.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the message's channel

        message_id: :class:`int`
            The id of the message

        emoji: :class:`str`
            The emoji to remove

        user_id: Optional[:class:`int`]
            The id of the user to remove the reaction from

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.NotFound`
            Either the channel_id, message_id, emoji, or user_id is invalid.

        :exc:`.BadRequest`
            You somehow messed up the payload.
        """
        base_path = f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}"
        final_path = base_path + f"/{user_id}" if user_id else base_path + "/@me"

        await self.request("DELETE", Route(final_path, channel_id=channel_id))

    async def get_reactions(
        self,
        channel_id: int,
        message_id: int,
        emoji: str,
        *,
        after: Optional[int] = None,
        limit: int = 25,
    ) -> dict:
        """A method to make an API call to get all the reactions of a message

        This method makes an API call to get the reactions of the specified message.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the message's channel

        message_id: :class:`int`
            The id of the message

        emoji: :class:`str`
            The emoji to get

        after: Optional[:class:`int`]
            Grabs users after this users id

        limit: :class:`int`
            The max amount of reactions to get

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.NotFound`
            Either the channel_id, message_id, emoji is invalid.

        :exc:`.BadRequest`
            You somehow messed up the payload.

        Returns
        -------
        List[:class:`dict`]
            A list of dicts representing a user who reacted.
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
    ) -> None:
        """A method which makes an API call to delete all reactions of a message.

        This method makes an API call to delete all the reactions of the specified message.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the message's channel

        message_id: :class:`int`
            The id of the message

        emoji: :class:`str`
            The emoji to remove from the message

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.NotFound`
            Either the channel_id, message_id or the emoji was invalid.

        :exc:`.Forbidden`
            Your client doesn't have permissions to delete all reactions.
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
        embeds: Optional[List[dict]] = None,
        allowed_mentions: Optional[dict] = None,
        attachments: Optional[List[dict]] = None,
        components: Optional[List[dict]] = None,
    ) -> dict:
        """A method which makes an API call to send a message.

        This method is used to send messages. This is used in :meth:`.TextChannel.send` and
        :meth:`.DMChannel.send`.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to send the messsage in

        message_id: :class:`int`
            The id of the message to edit

        content: Optional[:class:`str`]
            The content to edit the message with

        embeds: Optional[List[:class:`dict`]]
            A list of embeds to edit the message with. Only 10 embeds can be sent at a time

        allowed_mentions: Optional[:class:`dict`]
            A dict representing the allowed mentions to edit with

        attachments: Optional[List[:class:`dict`]]
            A list of attachments to edit the message with

        components: Optional[List[dict]]
            A list of message components to edit the message with

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making this request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to edit this message.

        :exc:`.BadRequest`
            You somehow messed up the payload.

        Returns
        -------
        :class:`dict`
            A dict representing the editted message object
        """
        payload: dict = {}
        update_payload(
            payload,
            content=content,
            embeds=embeds,
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

    async def delete_message(self, channel_id: int, message_id: int) -> None:
        """A method which makes an API call to delete a message.

        This method makes an API call to delete the specified message.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the message's channel

        message_id: :class:`int`
            The id of the message

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.NotFound`
            The message id is invalid or the specified message was deleted already.

        :exc:`.Forbidden`
            Your client doesn't have permissions to delete this message.
        """
        return await self.request(
            "DELETE",
            Route(
                f"/channels/{channel_id}/messages/{message_id}", channel_id=channel_id
            ),
        )

    async def bulk_delete_messages(
        self, channel_id: int, message_ids: List[int]
    ) -> None:
        """A method which makes an API call to bulk delete messages

        A method which makes an API call to bulk delete the list of specified messages.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the messages channel

        message_ids: List[:class:`int`]
            The list of ids of messages to delete

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc`.BadRequest`
            Either duplicate ids were given or one or more messages were
            older than two weeks.

        :exc:`.Forbidden`
            Your client doesn't have permissions to delete messages.
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
    ) -> None:
        """A method which makes an API to edit a channels overwrites

        This method makes an API call to edit the channels overwrites for the specified
        overwrite id. This can be a members's id or a role's.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel where the overwrite is in.

        overwrite_id: :class:`int`
            The id of the overwrite to edit

        allow: Optional[:class:`int`]
            The bitwise value of all allowed permissions

        deny: Optional[:class:`int`]
            The bitwise value of all disallowed permissions

        type: Optional[:class:`int`]
            The type of the target. 0 for a role and 1 for a member

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your clien't doesn't have permissions to edit this overwrite.
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
    ) -> None:
        """A method which makes an API call to delete an overwrite from the channel.

        This method calls the API to delete the specified overwrite from the channel.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel where the overwrite is in

        overwrite_id: :class:`int`
            The id of the overwrite

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to delete the overwrite.
        """
        return await self.request(
            "DELETE",
            Route(
                f"/channels/{channel_id}/permissions/{overwrite_id}",
                channel_id=channel_id,
            ),
        )

    async def get_channel_invites(self, channel_id: int) -> List[dict]:
        """A method which makes an API call to get a channels invites.

        This method makes an API call to get the invites of a specified channel.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to fetch invites from

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc`.Forbidden`
            Your client doesn't have permissions to get this channel invites.

        Returns
        -------
        List[:class:`dict`]
            A list of dicts that represents invites.
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
        """A method which makes an API call to create an invite.

        This method makes an API call to create an invite on the specified channel.
        If no max_age is passed it defaults to 24 hours. And max_uses defaults to 0

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to create the invite in

        max_age: :class:`int`
            The max age of the invite before expiring

        max_uses: :class:`int`
            The amount of times the invite can be used before going invalid

        temporary: :class:`bool`
            If the invite should grant temporary membership

        unique: :class:`bool`
            If the invite should be unique, used for one time use invites

        target_type: Optional[:class:`int`]
            The type of the invite. For voice channels

        target_user_id: Optional[:class:`int`]
            The id of the user whose stream to invite to. For voice channels

        target_application_id: Optional[:class:`int`]
            The id of embedded application to invite from. For target type 2

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to create an invite.

        Returns
        -------
        :class:`dict`
            A dict representing an invite object.
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
    ) -> dict:
        """A method which makes an API call to follow a news channel.

        This method makes an API call which makes the client follow the
        specified news channel.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the news channel

        webhook_channel_id: :class:`int`
            The target channel id to send the messages to

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to do this.

        Returns
        -------
        :class:`dict`
            A dict representing a followed channel.
        """
        payload = {"webhook_channel_id": webhook_channel_id}
        return await self.request(
            "PUT",
            Route(f"/channels/{channel_id}/followers/@me", channel_id=channel_id),
            json=payload,
        )

    async def trigger_typing(self, channel_id: int) -> None:
        """A method which makes the client start typing.

        This method makes and API call to make the client start typing
        in the specified channel.

        .. note::

            You generally shouldn't use this unless your doing an action
            which requires some computation time.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel where you want to start typig

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.
        """
        return await self.request(
            "POST", Route(f"/channels/{channel_id}/typing", channel_id=channel_id)
        )

    async def get_pinned_messages(self, channel_id: int) -> List[dict]:
        """A method which makes an API call to get a channel's pinned messages.

        A method which makes an API call to get a channel's pinned messages.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel to get the messages from

        Raises
        ------
        :exc:`.Forbidden`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`dict`]
            A list of dicts representing message objects.
        """
        return await self.request(
            "GET", Route(f"/channels/{channel_id}/pins", channel_id=channel_id)
        )

    async def pin_message(self, channel_id: int, message_id: int) -> None:
        """A method which makes an API call to ping a message.

        This method makes an API call which pins the specified message inside
        of the passed in channel. This is used in :meth:`.Message.pin`

        .. note::

            Max amount of pins in a channel is capped at 50

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel where the message is

        message_id: :class:`int`
            The id of the message to pin

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to pin this message.
        """
        return await self.request(
            "PUT",
            Route(f"/channels/{channel_id}/pins/{message_id}", channel_id=channel_id),
        )

    async def unpin_message(self, channel_id: int, message_id: int) -> None:
        """A method which makes an API call to unpin a message.

        This method makes an API call to unpin the passed in message from
        the specified channel. This is used in :meth:`.Message.unpin`

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel where the message is in

        message_id: :class:`int`
            The id of the message to unpin

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to unpin this message.
        """
        return await self.request(
            "DELETE",
            Route(f"/channels/{channel_id}/pins/{message_id}", channel_id=channel_id),
        )

    async def start_thread_with_message(
        self,
        channel_id: int,
        message_id: int,
        *,
        name: str,
        auto_archive_duration: Optional[int] = None,
    ) -> dict:
        """A method which makes an API call to start a thread.

        This method makes an API call to start a thread with a message.
        This is used in :meth:`.Message.create_thread`.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel where the message is

        message_id: :class:`int`
            The message's id

        name: :class:`str`
            The name of the thread

        auto_archive_duration: Optional[:class:`int`]
            How long it takes before the thread automatically archives

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to do this.

        :exc:`.BadRequest`
            You messed up the payload somehow.

        Returns
        -------
        :class:`dict`
            A dict representing the newly created thread channel.
        """
        payload = update_payload(
            {}, name=name, auto_archive_duration=auto_archive_duration
        )
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
        auto_archive_duration: Optional[int] = None,
        type: Optional[int] = None,
        invitable: Optional[bool] = None,
    ) -> dict:
        """A method which makes an API call to start a thread.

        This method makes an API call to start a thread without a message.
        This is used in :meth:`.TextChannel.create_thread`.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel where to create the thread from

        name: :class:`str`
            The name of the thread

        auto_archive_duration: Optional[:class:`int`]
            How long it takes before the thread automatically archives

        type: Optional[:class:`int`]
            The type of the thread

        invitable: Optional[:class:`bool`]
            If the thread should allow non-moderators to add people

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to do this.

        :exc:`.BadRequest`
            You messed up the payload somehow.

        Returns
        -------
        :class:`dict`
            A dict representing the newly created thread channel.
        """
        payload = update_payload(
            {},
            name=name,
            auto_archive_duration=auto_archive_duration,
            type=type,
            invitable=invitable,
        )

        return await self.request(
            "POST",
            Route(f"/channels/{channel_id}/threads", channel_id=channel_id),
            json=payload,
        )

    async def join_thread(self, channel_id: int) -> None:
        """Makes an API call which makes the client join the given thread.

        This method makes an API call which makes the client join the passed in
        thread. This is used in :meth:`.Thread.join`

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the thread to join

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.
        """
        return await self.request(
            "PUT",
            Route(f"/channels/{channel_id}/thread-members/@me", channel_id=channel_id),
        )

    async def add_thread_member(self, channel_id: int, member_id: int) -> None:
        """A method which adds a member to the specified thread

        This method makes an API call to add a member to the specified
        thread. You must be able to send messages in the thread and the thread
        cannot be archived in order to do this.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the thread channel

        member_id: :class:`int`
            The id of the member to add

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.
        """
        return await self.request(
            "PUT",
            Route(
                f"/channels/{channel_id}/thread-members/{member_id}",
                channel_id=channel_id,
            ),
        )

    async def leave_thread(self, channel_id: int) -> None:
        """A method hwich makes the client leave a thread.

        This method makes an API call which makes the client leave
        the specified thread channel.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the thread channel to leave

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.
        """
        return await self.request(
            "DELETE",
            Route(f"/channels/{channel_id}/thread-members/@me", channel_id=channel_id),
        )

    async def remove_thread_member(self, channel_id: int, member_id: int) -> None:
        """A method which removes a member from the thread.

        This method makes an API call to remove the specified member from a thread.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the thread channel to remove from

        member_id: :class:`int`
            The id of the member to remove

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to remove this member.
        """
        return await self.request(
            "DELETE",
            Route(
                f"/channels/{channel_id}/thread-members/{member_id}",
                channel_id=channel_id,
            ),
        )

    async def list_thread_members(self, channel_id: int) -> List[dict]:
        """A method which gets a thread channel's members.

        A method which makes an API call to get a list of all
        members inside of a thread channel.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the thread channel

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`dict`]
            A list of dicts representing a thread member.
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
    ) -> dict:
        """A method which gets all public archived threads.

        This method makes an API call which list all the public archived
        threads in the channel. This is used in :meth:`.TextChannel.fetch_archived_threads`

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel where to fetch from

        before: Optional[:class:`int`]
            Grab threads before this ISO8601 timestamp

        limit: Optional[:class:`int`]
            The max amount of threads to return

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to do this.

        Returns
        -------
        :class:`dict`
            A dict which contains a list of members and archive threads.
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
    ) -> dict:
        """A method which gets all private archived threads.

        This method makes an API call which list all the private archived
        threads in the channel. This is used in :meth:`.TextChannel.fetch_archived_threads`

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel where to fetch from

        before: Optional[:class:`int`]
            Grab threads before this ISO8601 timestamp

        limit: Optional[:class:`int`]
            The max amount of threads to return

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to do this.

        Returns
        -------
        :class:`dict`
            A dict which contains a list of members and archive threads.
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
    ) -> dict:
        """A method which gets all joined private archived threads.

        This method makes an API call which list all the joined private
        archived threads in the channel.

        Parameters
        ----------
        channel_id: :class:`int`
            The id of the channel where to fetch from

        before: Optional[:class:`int`]
            Grab threads before this ISO8601 timestamp

        limit: Optional[:class:`int`]
            The max amount of threads to return

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to do this.

        Returns
        -------
        :class:`dict`
            A dict which contains a list of members and archive threads.
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

    async def list_guild_emojis(self, guild_id: int) -> List[dict]:
        """A method which lists the guild's emojis.

        This method makes an API call to get a list of the guilds emojis.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild to fetch from

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`dict`]
            A list of dicts representing emojis.
        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/emojis", guild_id=guild_id)
        )

    async def get_guild_emoji(self, guild_id: int, emoji_id: int) -> dict:
        """A method which gets an emoji from a guild.

        This method makes an API call to get an emoji from the guild.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild to fetch from

        emoji_id: :class:`int`
            The emoji's id

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`dict`
            A dict representing the emoji.
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
    ) -> dict:
        """A method which makes an emoji in a guild.

        A method whick makes an API call to create an emoji inside
        of a guild.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild where to make the emoji in

        name: :class:`str`
            The name of the emoji

        image: :class:`bytes`
            The image of the emoji

        roles: Optional[List[:class:`int`]]
            A list of roles allowed to use this emoji

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to create this emoji.

        :exc:`.BadRequest`
            You somehow messed up the payload.

        Returns
        -------
        :class:`dict`
            A dict representing the created emoji.
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
    ) -> dict:
        """A method which edits a guild emoji.

        This method makes an API call to edit an emoji.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild where the emoji is in

        emoji_id: :class:`int`
            The id of the emoji to edit

        name: :class:`str`
            The new name of the emoji

        roles: Optional[List[:class:`int`]]
            A list of new roles which can use this emoji

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to edit this emoji.

        :exc:`.BadRequest`
            You somehow messed up the payload.

        Returns
        -------
        :class:`dict`
            The updated emoji object
        """
        payload = {"name": name}
        update_payload(payload, roles=roles)

        return await self.request(
            "PATCH",
            Route(f"/guilds/{guild_id}/emojis/{emoji_id}", guild_id=guild_id),
            json=payload,
        )

    async def delete_guild_emoji(self, guild_id: int, emoji_id: int) -> None:
        """A method which deletes an emoji from the guild.

        This method makes an API call which deletes an emoji.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild where the emoji is in

        emoji_id: :class:`int`
            The id of the emoji

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to delete this emoji.
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
        roles: Optional[List[dict]] = None,
        channels: Optional[List[dict]] = None,
        afk_channel: Optional[int] = None,
        afk_timeout: Optional[int] = None,
        system_channel_id: Optional[int] = None,
        system_channel_flags: Optional[int] = None,
    ) -> dict:
        """A method which creates a guild.

        This method makes an API call to create a guild.

        .. note::

            This endpoint can only be used for bots in less
            than 10 guilds.

        Parameters
        ----------
        name: :class:`str`
            The name of the guild

        region: Optional[:class:`str`]
            The region of the guild

        icon: Optional[:class:`bytes`]
            The icon of the guild

        verification_level: [:class:`int`]
            The verification level of the guild

        default_message_notifications: Optional[:class:`int`]
            The default message notification level

        explicit_content_filter: Optiona[:class:`int`]
            The explicit content filter filter of the guild

        roles: Optional[List[:class:`dict`]]
            A list of roles to make the guild with

        channels: Optional[List[:class:`dict`]]
            A list of channels to make the guild with

        afk_channel: Optional[:class:`int`]
            The afk channel of the guild

        afk_timeout: Optional[:class:`int`]
            The afk timeout in seconds

        system_channel_id: Optional[:class:`int`]
            The channel id for where to send system messages

        system_channel_flags: Optional[:class:`int`]
            The system channel flags

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`dict`
            A dict representing the newly created guild object.
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

    async def get_guild(self, guild_id: int, *, with_counts: bool = False) -> dict:
        """A method which fetches a guild.

        A method which makes an API call to get a guild corresponding
        to the passed in id.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild to fetch

        with_counts: :class:`int`
            If the API should return approximate member count and presence count

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.NotFound`
            The guild id passed is invalid.

        Returns
        -------
        :class:`dict`
            A dict representing the guild object.
        """
        params = {"with_counts": with_counts}
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}", guild_id=guild_id), params=params
        )

    async def get_guild_preview(self, guild_id: int) -> dict:
        """A method which fetches the guild's preview.

        A method which makes an API call to get a guild's preview.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild to fetch from

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`dict`
            A dict representing the guild's preview
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
        """A method which edits a guild.

        This method makes an API call to edit a guild.

        Parameters
        ----------
        name: :class:`str`
            The name of the guild

        region: Optional[:class:`str`]
            The region of the guild

        icon: Optional[:class:`bytes`]
            The icon of the guild

        verification_level: [:class:`int`]
            The verification level of the guild

        default_message_notifications: Optional[:class:`int`]
            The default message notification level

        explicit_content_filter: Optiona[:class:`int`]
            The explicit content filter filter of the guild

        roles: Optional[List[:class:`dict`]]
            A list of roles to make the guild with

        channels: Optional[List[:class:`dict`]]
            A list of channels to make the guild with

        afk_channel: Optional[:class:`int`]
            The afk channel of the guild

        afk_timeout: Optional[:class:`int`]
            The afk timeout in seconds

        system_channel_id: Optional[:class:`int`]
            The channel id for where to send system messages

        system_channel_flags: Optional[:class:`int`]
            The system channel flags

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`dict`
            A dict representing the modified guild object.
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

    async def delete_guild(self, guild_id: int) -> None:
        """A method which deletes a guild.

        This method makes an API call to delete a guild.
        The client must be the owner of the guild.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild to delete

        Raises
        ------
        :class:`.HTTPException`
            Something went wrong while making the request.
        """
        await self.request("DELETE", Route(f"/guilds/{guild_id}", guild_id=guild_id))

    async def get_guild_channels(self, guild_id: int) -> List[dict]:
        """A method which grabs the channels of a guild.

        This method makes an API call to get a guild's channels.
        This API call does not include thread channels.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild to fetch from

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`dict`]
            A list of dicts representing channels.
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
        permission_overwrites: Optional[List[dict]] = None,
        parent_id: Optional[int] = None,
        nsfw: Optional[bool] = None,
    ) -> dict:
        """A method which creates a guild channel.

        This method makes an API call to create a channel in a guild.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild where the channel should be in

        name: :class:`str`
            The name of the channel

        type: Optional[:class:`int`]
            The type of channel to create

        topic: Optional[:class:`str`]
            The topic of the channel

        bitrate: Optional[:class:`int`]
            The bitrate of the channel. Used if its a voice channel

        user_limit: Optional[:class:`int`]
            The max amount of users that can be in the channel. This is used for voice
            channels

        position: Optional[:class:`int`]
            The position of the channel

        permission_overwrites: Optional[List[:class:`dict`]]
            A list of permission overwrites for the channel

        parent_id: Optional[:class:`int`]
            The parent channel's id

        nsfw: Optional[:class:`bool`]
            If the channel should be marked as NSFW

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to create this channel.

        Returns
        -------
        :class:`dict`
            A dict representing the newly created channel.
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

    async def list_active_threads(self, guild_id: int) -> dict:
        """A method which list all active threads in a guild.

        This method makes an API call to get a guild's active threads.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild to fetch from

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`dict`
            A dict which contains a list of thread channels and a list
            of thread member objects.
        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/threads/active", guild_id=guild_id)
        )

    async def get_guild_member(self, guild_id: int, member_id: int) -> Dict[str, Any]:
        """A method which fetches a member from a guild.

        This method makes an API call to get a guild member.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild to fetch from.

        member_id: :class:`int`
            The member to fetch

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.NotFound`
            The member id was invalid.

        Returns
        -------
        :class:`dict`
            A dict representing the member object.
        """
        return await self.request(
            "GET", Route(f"/guilds/{guild_id}/members/{member_id}", guild_id=guild_id)
        )

    async def get_guild_audit_log(
        self,
        guild_id: int,
        *,
        user_id: Optional[int] = None,
        action_type: Optional[int] = None,
        before: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> dict:
        """A method which fetches an audit log.

        This method makes an API call to get an audit log
        from the specified guild.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild to fetch from

        user_id: Optional[:class:`int`]
            The user to filter for

        action_type: Optional[:class:`int`]
            The action type to filter for

        before: Optional[:class:`int`]
            filter before this entry id

        limit: Optional[:class:`int`]
            The max amount of entries to return

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`dict`
            A dict representing an audit log
        """
        params = update_payload(
            {},
            user_id=user_id,
            action_type=action_type,
            before=before,
            limit=limit,
        )

        return await self.request(
            "GET",
            Route(f"/guilds/{guild_id}/audit-logs", guild_id=guild_id),
            params=params,
        )

    async def list_guild_members(
        self, guild_id: int, *, limit: int = 1, after: Optional[int] = None
    ) -> List[dict]:
        """This method fetches a list of members.

        This method makes an API call to get a list of the guild's members.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild to fetch from

        limit: :class:`int`
            The max amount of members to return

        after: Optional[:class:`int`]
            List members after this member's id

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`dict`]
            A list of member objects fetched.
        """
        params = update_payload({}, limit=limit, after=after)
        return await self.request(
            "GET",
            Route(f"/guilds/{guild_id}/members", guild_id=guild_id),
            params=params,
        )

    async def search_guild_members(
        self, guild_id: int, *, query: str, limit: int = 1
    ) -> List[dict]:
        """This method searches the guild's members.

        This method makes an API call to search a guild's members
        corresponding to the query passed.

        Parameters
        ----------
        guild_id: :class:`int`
            The id of the guild to fetch from

        query: :class:`str`
            The username or nickname to search for

        limit: :class:`int`
            The max amount of members to return

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        List[:class:`dict`]
            A list of dicts representing a member object.
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

    async def get_guild_roles(self, guild_id: int) -> List[Dict[str, Any]]:
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
    ) -> Dict[str, Any]:
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

        return await self.request(
            "POST", Route(f"/guilds/{guild_id}/prune", guild_id=guild_id), json=payload
        )

    async def get_guild_voice_regions(self, guild_id: int) -> List[Dict[str, Any]]:
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

    async def get_user(self, user_id) -> Dict:
        return await self.request("GET", Route(f"users/{user_id}"))

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
        file: Optional[File] = None,
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
            file (Optional[File]): The file to upload.
            embeds (Optional[List[Dict[str, Any]]]): The embeds to send.
            allowed_mentions (Optional[Dict[str, Any]]): The allowed mentions.
            componenets (Optional[List[Dict[str, Any]]]): The components to send.
            wait (Optional[bool]): Whether to wait for server confirmation  before response.
            thread_id (Optional[int]): The ID of the thread to post to.

        Returns:
            The data returned from the API.

        """
        form = self.form_helper([file])
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
        file: Optional[File] = None,
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
            file (Optional[File]): The file to upload.
            allowed_mentions (Optional[Dict[str, Any]]): The allowed mentions.
            componenets (Optional[List[Dict[str, Any]]]): The components to send.
            attachments (Optional[List[Dict[str, Any]]]): The attachments to send.

        Returns:
            The data returned from the API.

        """
        form = self.form_helper([file])
        payload = update_payload(
            {},
            content=content,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            componenets=componenets,
            attachments=attachments,
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
        file: Optional[File] = None,
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
            file (Optional[File]): The file of the response.
            allowed_mentions (Optional[Dict[str, Any]]): The allowed mentions of the response.
            componenets (Optional[List[Dict[str, Any]]]): The components of the response.
            attachments (Optional[List[Dict[str, Any]]]): The attachments of the response.

        Returns:
            The data returned from the API.

        """
        form = self.form_helper([file])
        payload = update_payload(
            {},
            content=content,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            componenets=componenets,
            attachments=attachments,
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
        file: Optional[File] = None,
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
            file (Optional[File]): The file of the response.
            allowed_mentions (Optional[Dict[str, Any]]): The allowed mentions of the response.
            componenets (Optional[List[Dict[str, Any]]]): The components of the response.
            attachments (Optional[List[Dict[str, Any]]]): The attachments of the response.
            flags (Optional[int]): The flags of the response.

        Returns:
            The data returned from the API.

        """
        form = self.form_helper([file])
        payload = update_payload(
            {},
            content=content,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            componenets=componenets,
            attachments=attachments,
            flags=flags,
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
        file: Optional[File] = None,
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
            file (Optional[File]): The file of the response.
            allowed_mentions (Optional[Dict[str, Any]]): The allowed mentions of the response.
            componenets (Optional[List[Dict[str, Any]]]): The components of the response.
            attachments (Optional[List[Dict[str, Any]]]): The attachments of the response.

        Returns:
            The data returned from the API.

        """
        form = self.form_helper([file])
        payload = update_payload(
            {},
            content=content,
            embeds=embeds,
            allowed_mentions=allowed_mentions,
            componenets=componenets,
            attachments=attachments,
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

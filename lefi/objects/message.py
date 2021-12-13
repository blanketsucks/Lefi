from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Union
import datetime

from lefi.utils.payload import update_payload

from ..utils import Snowflake
from .embed import Embed
from .threads import Thread
from .attachments import Attachment
from .components import ActionRow
from .mentions import AllowedMentions

if TYPE_CHECKING:
    from ..state import State
    from .channel import DMChannel, TextChannel
    from .guild import Guild
    from .member import Member
    from .user import User

    Channels = Union[TextChannel, DMChannel]

__all__ = ("Message", "DeletedMessage")


class DeletedMessage:
    """Represents a deleted message.

    This is given instead of a regular :class:`.Message` in `MESSAGE_DELETE` if the
    message isn't cached beforehand.

    Attributes
    ----------
    id: :class:`int`
        The id of the message

    channel_id: :class:`int`
        The id of the message's channel

    guild_id: Optional[:class:`int`]
        The id of the guild where the message was deleted, if there is one
    """

    def __init__(self, data: dict) -> None:
        self.id = int(data["id"])
        self.channel_id = int(data["channel_id"])
        self.guild_id = int(data["guild_id"]) if "guild_id" in data else None


class Message:
    """Represents a message."""

    def __init__(self, state: State, data: dict, channel: Channels) -> None:
        self._channel = channel
        self._state = state
        self._data = data

        self._pinned = data.get("pinned", False)

    def __repr__(self) -> str:
        return f"<Message id={self.id}>"

    async def edit(
        self,
        content: Optional[str] = None,
        *,
        embeds: Optional[List[Embed]] = None,
        allowed_mentions: Optional[AllowedMentions] = None,
        attachments: Optional[List[Attachment]] = None,
        rows: Optional[List[ActionRow]] = None,
    ) -> Message:
        """Edits the message.

        Parameters
        ----------
        content: Optional[:class:`str`]
            The new content of the message

        embeds: Optional[List[Embed]]
            A list of new embeds for the message, max is 10 embeds at a time

        allowed_mentions: Optional[AllowedMentions]
            The new allowed mentions of the message

        attachments: Optional[List[Attachment]]
            A list of new attachments to edit the message with

        rows: Optional[List[ActionRow]]
            A list of action rows to send with the message

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to edit this message.

        Returns
        -------
        :class:`.Message`
            The message after editting.
        """
        req = self._state.client.http.edit_message

        embeds_ = [e.to_dict() for e in embeds] if embeds else []
        actionrows_ = [r.to_dict() for r in rows] if rows else []
        attachments_ = [a.to_dict() for a in attachments] if attachments else []
        mentions = allowed_mentions.to_dict() if allowed_mentions else None

        data = await req(
            channel_id=self.channel.id,
            message_id=self.id,
            content=content,
            embeds=embeds_,
            components=actionrows_,
            allowed_mentions=mentions,
            attachments=attachments_,
        )

        rows = rows or []
        for row in rows:
            row._cache_components(self._state)

        self._data = data
        return self

    async def crosspost(self) -> Message:
        """Crossposts the message.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        Returns
        -------
        :class:`.Message`
            The message being crossposted.
        """
        data = await self._state.http.crosspost_message(self.channel.id, self.id)
        return self._state.create_message(data, self.channel)

    async def add_reaction(self, reaction: str) -> None:
        """Adds a reaction to the message.

        Parameters
        ----------
        reaction: :class:`str`
            The reaction to add

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.
        """
        await self._state.http.create_reaction(channel_id=self.channel.id, message_id=self.id, emoji=reaction)

    async def remove_reaction(self, reaction: str, user: Optional[Snowflake] = None) -> None:
        """Removes a reaction from the message.

        Parameters
        ----------
        reaction: :class:`str`
            The reaction to remove from the message

        user: Optional[:class:`.Snowflake`]
            The user to remove the reaction from

        Raises
        ------
        :exc:`.HTTPException`
            SOmething went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to remove this reaction.
        """
        await self._state.http.delete_reaction(
            channel_id=self.channel.id,
            message_id=self.id,
            emoji=reaction,
            user_id=user.id if user is not None else user,
        )

    async def pin(self) -> None:
        """Pins the message.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to pin this message.
        """
        await self._state.http.pin_message(self.channel.id, self.id)
        self._pinned = True

    async def unpin(self) -> None:
        """Unpins the message.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to unpin this message.
        """
        await self._state.http.unpin_message(self.channel.id, self.id)
        self._pinned = False

    async def delete(self) -> None:
        """Deletes the message.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to delete this message.
        """
        await self._state.http.delete_message(self.channel.id, self.id)
        self._state._messages.pop(self.id, None)

    async def create_thread(self, *, name: str, auto_archive_duration: Optional[int] = None) -> Thread:
        """Creates a thread from the message.

        Parameters
        ----------
        name: :class:`str`
            The name of the thread

        auto_archive_duration: Optional[:class:`int`]
            The time it takes to auto archive the thread

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.

        :exc:`.Forbidden`
            Your client doesn't have permissions to create this thread.

        Returns
        -------
        :class:`.Thread`
            The newly created thread.
        """
        if not self.guild:
            raise TypeError("Cannot a create thread in a DM channel.")

        if auto_archive_duration is not None:
            if auto_archive_duration not in (60, 1440, 4320, 10080):
                raise ValueError("auto_archive_duration must be 60, 1440, 4320 or 10080")

        data = await self._state.http.start_thread_with_message(
            channel_id=self.channel.id,
            message_id=self.id,
            name=name,
            auto_archive_duration=auto_archive_duration,
        )

        return Thread(self._state, self.guild, data)

    def to_reference(self) -> dict:
        """Creates a reference dict from the message.

        This is used for replies.

        Returns
        -------
        :class:`dict`
            The created dict for the message.
        """
        payload = {"message_id": self.id, "channel_id": self.channel.id}

        if self.guild:
            payload["guild_id"] = self.guild.id

        return payload

    @property
    def id(self) -> int:
        """The id of the message."""
        return int(self._data["id"])

    @property
    def created_at(self) -> datetime.datetime:
        """The time the message was created at."""
        return datetime.datetime.fromisoformat(self._data["timestamp"])

    @property
    def channel(self) -> Channels:
        """The channel which the message belongs to."""
        return self._channel

    @property
    def guild(self) -> Optional[Guild]:
        """The guild which the message belongs to."""
        return self._channel.guild

    @property
    def content(self) -> str:
        """The content of the message."""
        return self._data["content"]

    @property
    def author(self) -> Union[User, Member]:
        """The author of the message."""
        if self.guild is None:
            return self._state.get_user(int(self._data["author"]["id"]))  # type: ignore

        if author := self.guild.get_member(int(self._data["author"]["id"])):  # type: ignore
            return author
        else:
            return self._state.add_user(self._data["author"])

    @property
    def embeds(self) -> List[Embed]:
        """The embeds of the message."""
        return [Embed.from_dict(embed) for embed in self._data["embeds"]]

    @property
    def attachments(self) -> List[Attachment]:
        """The attachments of the message."""
        return [Attachment(self._state, attachment) for attachment in self._data["attachments"]]

    @property
    def pinned(self) -> bool:
        """Whether the message is pinned or not."""
        return self._pinned

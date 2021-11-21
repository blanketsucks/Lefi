from __future__ import annotations

from typing import TYPE_CHECKING, Optional, List, Callable, Iterable
import asyncio
import datetime

from .embed import Embed
from .files import File
from .components import ActionRow
from ..utils import Snowflake, ChannelHistoryIterator, grouper
from .mentions import AllowedMentions

if TYPE_CHECKING:
    from .message import Message
    from ..state import State

__all__ = ("Messageable", "BaseTextChannel")


class Messageable(Snowflake):
    """Represents a messageable object."""

    _state: State

    async def send(
        self,
        content: Optional[str] = None,
        *,
        tts: bool = False,
        embed: Optional[Embed] = None,
        embeds: Optional[List[Embed]] = None,
        reference: Optional[Message] = None,
        file: Optional[File] = None,
        files: Optional[List[File]] = None,
        rows: Optional[List[ActionRow]] = None,
        allowed_mentions: Optional[AllowedMentions] = None,
        **kwargs,
    ) -> Message:
        """Sends a message to the target.

        Parameters
        ----------
        content: Optional[:class:`str`]
            The content of the message

        tts: :class:`bool`
            Whether or not the message is sent with text-to-speech

        embed: Optional[:class:`.Embed`]
            The embed to send with the message

        embeds: Optional[List[:class:`.Embed`]]
            The list of embeds to send with the message

        reference: Optional[:class:`.Message`]
            References a message when sending

        file: Optional[:class:`.File`]
            A file to send with the message

        files: Optional[List[:class:`.File`]]
            The list of files to send with the message

        rows: Optional[List[:class:`.ActionRow`]]
            A list of action rows to send with the message

        allowed_mentions: Optional[:class:`.AllowedMentions`]
            The allowed mentions of this message

        **kwargs: Any
            Extra options to pass to :meth:`.HTTPClient.send_message`

        Returns
        -------
        :class:`.Message`
            A message object representing the sent message.
        """
        embeds = [] if embeds is None else embeds
        files = [] if files is None else files

        message_reference = None

        if embed is not None:
            embeds.append(embed)

        if file is not None:
            files.append(file)

        if reference is not None:
            message_reference = reference.to_reference()

        data = await self._state.http.send_message(
            channel_id=self.id,
            content=content,
            tts=tts,
            embeds=[embed.to_dict() for embed in embeds],
            message_reference=message_reference,
            files=files,
            components=[row.to_dict() for row in rows] if rows is not None else None,
            allowed_mentions=allowed_mentions.to_dict()
            if allowed_mentions is not None
            else None,
            **kwargs,
        )

        message = self._state.create_message(data, self)

        if rows is not None and data.get("components"):
            for row in rows:
                for component in row.components:
                    self._state._components[component.custom_id] = (
                        component.callback,
                        component,
                    )

        return message

    async def fetch_message(self, message_id: int) -> Message:
        """Fetches a message.

        This method makes an API call to fetch a message.

        Parameters
        ----------
        message_id: :class:`int`
            The id of the message to fetch

        Returns
        -------
        :class:`.Message`
            The fetched message object.
        """
        data = await self._state.http.get_channel_message(self.id, message_id)
        return self._state.create_message(data, self)

    async def fetch_pins(self) -> List[Message]:
        """Fetches a list of pinned messages.

        This method makes an API call to get the list of pinned messages.

        Returns
        -------
        List[:class:`.Message`]
            The list of pinned messages.
        """
        data = await self._state.http.get_pinned_messages(self.id)
        return [self._state.create_message(m, self) for m in data]

    def history(self, **kwargs) -> ChannelHistoryIterator:
        """Fetches the history of messages.

        Parameters
        ----------
        kwargs: Any
            The options to pass to :meth:`.HTTPClient.get_channel_messages`

        Returns
        -------
        :class:`.ChannelHistoryIterator`
            An Iterator for the channel's history
        """
        coro = self._state.http.get_channel_messages(self.id, **kwargs)
        return ChannelHistoryIterator(self._state, self, coro)


class BaseTextChannel(Messageable):
    """A base class for text channels."""

    async def delete_messages(self, messages: Iterable[Message]) -> None:
        """Deletes messages from the channel.

        Parameters
        ----------
        messages: Iterable[:class:`.Message`]
            The messages to delete
        """
        await self._state.http.bulk_delete_messages(
            self.id, message_ids=[msg.id for msg in messages]
        )

    async def purge(
        self,
        *,
        limit: int = 100,
        check: Optional[Callable[[Message], bool]] = None,
        around: Optional[int] = None,
        before: Optional[int] = None,
        after: Optional[int] = None,
    ) -> List[Message]:
        """Purges messages from the channel.

        Parameters
        ----------
        limit: :class:`int`
            How many messages to delete

        check: Optional[Callable[[Message], :class:`bool`]]
            The check that needs to be passed for a message to be deleted

        around: Optional[:class:`int`]
            Delete messages around this message id

        before: Optional[:class:`int`]
            Delete messages before this message id

        after: Optional[:class:`int`]
            Delete messages after this message id

        Returns
        -------
        List[:class:`.Message`]
            A list of the deleted messages.
        """
        now = datetime.datetime.utcnow()

        if not check:
            check = lambda _: True

        iterator = self.history(limit=limit, before=before, around=around, after=after)
        to_delete: List[Message] = [
            message async for message in iterator if check(message)
        ]

        for message in to_delete:
            delta = now - message.created_at

            if delta.days >= 14:
                await message.delete()
                to_delete.remove(message)

        for group in grouper(100, to_delete):
            if len(group) < 2:
                for message in group:
                    await message.delete()

                    continue

            await self.delete_messages(group)
            await asyncio.sleep(1)

        return to_delete

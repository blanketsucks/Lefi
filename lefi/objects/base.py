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
        """
        Sends a message to the channel.

        Parameters:
            content (Optional[str]): The content of the message.
            embeds (Optional[List[lefi.Embed]]): The list of embeds to send with the message.
            rows (Optional[List[ActionRow]]): The rows to send with the message.
            **kwargs (Any): Extra options to pass to
            [lefi.HTTPClient.send_message](./http.md#lefi.http.HTTPClient.send_message).

        Returns:
            The sent [lefi.Message](./message.md) instance.
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
        """
        Makes an API call to receive a message.

        Parameters:
            message_id (int): The ID of the message.

        Returns:
            The [lefi.Message](./message.md) instance corresponding to the ID if found.
        """
        data = await self._state.http.get_channel_message(self.id, message_id)
        return self._state.create_message(data, self)

    async def fetch_pins(self) -> List[Message]:
        """
        Fetches the pins of the channel.

        Returns:
            A list of [lefi.Message](./message.md) instances.
        """
        data = await self._state.http.get_pinned_messages(self.id)
        return [self._state.create_message(m, self) for m in data]

    def history(self, **kwargs) -> ChannelHistoryIterator:
        """
        Makes an API call to grab messages from the channel.

        Parameters:
            **kwargs (Any): The option to pass to
            [lefi.HTTPClient.get_channel_messages](./http.md#lefi.http.HTTPClient.get_channel_messages).

        Returns:
            A list of the fetched [lefi.Message](./message.md) instances.

        """
        coro = self._state.http.get_channel_messages(self.id, **kwargs)
        return ChannelHistoryIterator(self._state, self, coro)


class BaseTextChannel(Messageable):
    async def delete_messages(self, messages: Iterable[Message]) -> None:
        """
        Bulk deletes messages from the channel.

        Parameters:
            messages (Iterable[lefi.Message]): The list of messages to delete.

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
        """
        Purges messages from the channel.

        Parameters:
            limit (int): The maximum number of messages to delete.
            check (Callable[[lefi.Message], bool]): A function to filter messages.
            around (int): The time around which to search for messages to delete.
            before (int): The time before which to search for messages to delete.
            after (int): The time after which to search for messages to delete.

        Returns:
            A list of the deleted [lefi.Message](./message.md) instances.
        """
        now = datetime.datetime.utcnow()

        if not check:
            check = lambda message: True

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

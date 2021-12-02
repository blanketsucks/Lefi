from __future__ import annotations
import asyncio

from typing import TYPE_CHECKING, Dict, List, Optional
import datetime

from ..utils import to_snowflake
from .base import BaseTextChannel

if TYPE_CHECKING:
    from ..state import State
    from .channel import TextChannel
    from .guild import Guild
    from .member import Member
    from .message import Message
    from .user import User

__all__ = ("Thread", "ThreadMember")


class Thread(BaseTextChannel):
    """Represents a thread."""

    def __init__(self, state: State, guild: Guild, data: dict) -> None:
        self._state = state
        self._guild = guild
        self._data = data
        self._metadata = data["thread_metadata"]

        self._members: Dict[int, ThreadMember] = {}

    def __repr__(self) -> str:
        return f"<Thread id={self.id} name={self.name!r} owner_id={self.owner_id}>"

    def _copy(self) -> Thread:
        copy = self.__class__(self._state, self.guild, self._data)
        copy._members = self._members.copy()

        return copy

    @property
    def parent_id(self) -> Optional[int]:
        """The id of the parent channel."""
        return to_snowflake(self._data, "parent_id")

    @property
    def parent(self) -> Optional[TextChannel]:
        """The parent channel of the thread."""
        return self._guild.get_channel(self.parent_id)  # type: ignore

    @property
    def guild(self) -> Guild:
        """The guild which the thread belongs to."""
        return self.guild

    @property
    def name(self) -> str:
        """The name of the thread."""
        return self._data["name"]

    @property
    def id(self) -> int:  # type: ignore
        """The id of the thread."""
        return int(self._data["id"])

    @property
    def owner_id(self) -> int:
        """The id of the owner of the thread."""
        return int(self._data["owner_id"])

    @property
    def owner(self) -> Optional[Member]:
        """The owner of the thread."""
        return self.guild.get_member(self.owner_id)

    @property
    def message_count(self) -> int:
        """The number of messages in the thread."""
        return self._data["message_count"]

    @property
    def member_count(self) -> int:
        """The number of members in the thread."""
        return self._data["member_count"]

    @property
    def last_message_id(self) -> Optional[int]:
        """The in of the last message in the thread"""
        return to_snowflake(self._data, "last_message_id")

    @property
    def last_message(self) -> Optional[Message]:
        """The last message in the thread."""
        return self._state.get_message(self.last_message_id)  # type: ignore

    @property
    def members(self) -> List[ThreadMember]:
        """The members of the thread."""
        return list(self._members.values())

    @property
    def archived(self) -> bool:
        """Whether the thread is archived or not."""
        return self._metadata["archived"]

    @property
    def auto_archive_duration(self) -> int:
        """The duration in days after which the thread will be automatically archived."""
        return self._metadata["auto_archive_duration"]

    @property
    def archived_at(self) -> datetime.datetime:
        """The date and time when the thread's archive status was changed."""
        timestamp = self._metadata["archive_timestamp"]
        return datetime.datetime.fromisoformat(timestamp)

    @property
    def locked(self) -> bool:
        """Whether the thread is locked or not."""
        return self._metadata["locked"]

    @property
    def invitable(self) -> bool:
        """Whether the thread is invitable or not."""
        return self._metadata.get("invitable", False)

    async def join(self) -> None:
        """Makes the client user join the thread.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.
        """
        await self._state.http.join_thread(channel_id=self.id)

    async def leave(self) -> None:
        """Makes the client user leave the thread.

        Raises
        ------
        :exc:`.HTTPException`
            Something went wrong while making the request.
        """
        await self._state.http.leave_thread(channel_id=self.id)

    async def add_member(self, member: Member) -> None:
        """Adds a member to this thread.

        parameters
        ----------
        member: :class:`.member`
            the member to add to the thread

        Raises
        ------
        :exc:`.httpexception`
            something went wrong while making the request.

        :exc:`.forbidden`
            your client doesn't have permissions to add this member.
        """
        await self._state.http.add_thread_member(channel_id=self.id, member_id=member.id)

    async def remove_member(self, member: Member) -> None:
        """Removes a user from this thread.

        parameters
        ----------
        member: :class:`.member`
            the member to remove from the thread

        Raises
        ------
        :exc:`.httpexception`
            something went wrong while making the request.

        :exc:`.forbidden`
            your client doesn't have permissions to remove this member.
        """
        await self._state.http.remove_thread_member(channel_id=self.id, member_id=member.id)

    async def fetch_members(self) -> List[ThreadMember]:
        """Fetches the members of this thread.

        Raises
        ------
        :exc:`.httpexception`
            something went wrong while making the request.

        Returns
        -------
        List[:class:`.ThreadMember`]
            A list of the fetched members.
        """
        data = await self._state.http.list_thread_members(channel_id=self.id)
        return [ThreadMember(self._state, member, self) for member in data]

    async def delete(self) -> None:
        """Deletes this thread.

        Raises
        ------
        :exc:`.httpexception`
            something went wrong while making the request.
        """
        await self._state.http.delete_channel(channel_id=self.id)

    def get_member(self, member_id: int) -> Optional[ThreadMember]:
        """Gets a member from this thread.

        This grabs from the thread's member cache.

        Parameters
        ----------
        user_id: :class:`int`
            The id of the member to fetch

        Returns
        -------
        Optional[:class:`.ThreadMember`]
            The member corresponding to the passed in id.
        """
        return self._members.get(member_id)

    def _create_member(self, data: Dict) -> ThreadMember:
        member = ThreadMember(self._state, data, self)
        self._members[member.id] = member

        return member


class ThreadMember:
    """Represents a member of a thread."""

    def __init__(self, state: State, data: Dict, thread: Thread) -> None:
        self._state = state
        self._data = data
        self._thread = thread

    def __repr__(self) -> str:
        return f"<ThreadMember id={self.id} flags={self.flags}>"

    @property
    def id(self) -> int:
        """The id of the member."""
        return to_snowflake(self._data, "user_id") or self._state.user.id

    @property
    def flags(self) -> int:
        """The flags of the member."""
        return self._data["flags"]

    @property
    def thread(self) -> Thread:
        """The thread which the member belongs to."""
        return self._thread

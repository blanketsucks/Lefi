from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional
import datetime

from ..utils import to_snowflake

if TYPE_CHECKING:
    from ..state import State
    from .channel import TextChannel
    from .guild import Guild
    from .member import Member
    from .message import Message
    from .user import User

__all__ = ("Thread", "ThreadMember")


class Thread:
    def __init__(self, state: State, guild: Guild, data: Dict) -> None:
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
        """
        The ID of the parent channel. Could be None.
        """
        return to_snowflake(self._data, "parent_id")

    @property
    def parent(self) -> Optional[TextChannel]:
        """
        The parent channel of this thread. Could be None.
        """
        return self._guild.get_channel(self.parent_id)  # type: ignore

    @property
    def guild(self) -> Guild:
        """
        The guild this thread is in.
        """
        return self.guild

    @property
    def name(self) -> str:
        """
        The name of the thread.
        """
        return self._data["name"]

    @property
    def id(self) -> int:
        """
        The ID of the thread.
        """
        return int(self._data["id"])

    @property
    def owner_id(self) -> int:
        """
        The ID of the owner of the thread.
        """
        return int(self._data["owner_id"])

    @property
    def owner(self) -> Optional[Member]:
        """
        The owner of the thread. Could be None.
        """
        return self.guild.get_member(self.owner_id)

    @property
    def message_count(self) -> int:
        """
        The number of messages in the thread.
        """
        return self._data["message_count"]

    @property
    def member_count(self) -> int:
        """
        The number of members in the thread.
        """
        return self._data["member_count"]

    @property
    def last_message_id(self) -> Optional[int]:
        """
        The ID of the last message in the thread. Could be None.
        """
        return to_snowflake(self._data, "last_message_id")

    @property
    def last_message(self) -> Optional[Message]:
        """
        The last message in the thread. Could be None.
        """
        return self._state.get_message(self.last_message_id)  # type: ignore

    @property
    def members(self) -> List[ThreadMember]:
        """
        The members of the thread.
        """
        return list(self._members.values())

    @property
    def archived(self) -> bool:
        """
        Whether the thread is archived.
        """
        return self._metadata["archived"]

    @property
    def auto_archive_duration(self) -> int:
        """
        The duration in days after which the thread will be automatically archived.
        """
        return self._metadata["auto_archive_duration"]

    @property
    def archived_at(self) -> datetime.datetime:
        """
        The date and time when the thread's archive status was changed.
        """
        timestamp = self._metadata["archive_timestamp"]
        return datetime.datetime.fromisoformat(timestamp)

    @property
    def locked(self) -> bool:
        """
        Whether the thread is locked.
        """
        return self._metadata["locked"]

    @property
    def invitable(self) -> bool:
        """
        Whether the thread is invitable.
        """
        return self._metadata.get("invitable", False)

    async def join(self) -> None:
        """
        Joins this thread.
        """
        await self._state.http.join_thread(channel_id=self.id)

    async def leave(self) -> None:
        """
        Leaves this thread.
        """
        await self._state.http.leave_thread(channel_id=self.id)

    async def add_user(self, user: User) -> None:
        """
        Adds a user to this thread.

        Parameters:
            user (lefi.User): The user to add.
        """
        await self._state.http.add_thread_member(channel_id=self.id, user_id=user.id)

    async def remove_user(self, user: User) -> None:
        """
        Removes a user from this thread.

        Parameters:
            user (lefi.User): The user to remove.

        """
        await self._state.http.remove_thread_member(channel_id=self.id, user_id=user.id)

    async def fetch_members(self) -> List[ThreadMember]:
        """
        Fetches the members of this thread.

        Returns:
            a list of thread members.
        """
        data = await self._state.http.list_thread_members(channel_id=self.id)
        return [ThreadMember(self._state, member, self) for member in data]

    async def delete(self) -> None:
        """
        Deletes this thread.
        """
        await self._state.http.delete_channel(channel_id=self.id)

    def get_member(self, user_id: int) -> Optional[ThreadMember]:
        """
        Gets a member from this thread.

        Parameters:
            user_id (int): The ID of the user.

        Returns:
            the member if found.
        """
        return self._members.get(user_id)

    def _create_member(self, data: Dict) -> ThreadMember:
        member = ThreadMember(self._state, data, self)
        self._members[member.id] = member

        return member


class ThreadMember:
    def __init__(self, state: State, data: Dict, thread: Thread) -> None:
        self._state = state
        self._data = data
        self._thread = thread

    def __repr__(self) -> str:
        return f"<ThreadMember id={self.id} flags={self.flags}>"

    @property
    def id(self) -> int:
        """
        The ID of the member.
        """
        return to_snowflake(self._data, "user_id") or self._state.user.id

    @property
    def flags(self) -> int:
        """
        The flags of the member.
        """
        return self._data["flags"]

    @property
    def thread(self) -> Thread:
        """
        The thread of the member.
        """
        return self._thread

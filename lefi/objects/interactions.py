from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, Union, List

from lefi.utils.payload import update_payload

from .member import Member
from .embed import Embed
from .components import ActionRow


if TYPE_CHECKING:
    from .guild import Guild
    from .user import User
    from .channel import Channel, DMChannel
    from .message import Message
    from ..state import State

__all__ = ("Interaction",)


class Interaction:
    def __init__(self, state: State, data: Dict) -> None:
        self._state = state
        self._data = data

        self._user: Union[User, Member] = None  # type: ignore
        self._responded: bool = False

    @property
    def token(self) -> str:
        return self._data["token"]

    @property
    def application_id(self) -> int:
        return int(self._data["application_id"])

    @property
    def id(self) -> int:
        return int(self._data["id"])

    @property
    def responded(self) -> bool:
        return self._responded

    @property
    def channel(self) -> Optional[Union[Channel, DMChannel]]:
        if self.message is not None:
            return self.message.channel

        return self._state.get_channel(int(self._data["message"]["channel_id"]))

    @property
    def message(self) -> Message:
        if message := self._state.get_message(self._data["message"]["id"]):
            return message

        channel = self._state.get_channel(int(self._data["message"]["channel_id"]))
        return self._state.create_message(self._data["message"], channel)

    @property
    def user(self) -> Union[User, Member]:
        if self._user is None:
            self._user = self._create_user()

        return self._user

    @property
    def guild(self) -> Optional[Guild]:
        return self.message.guild

    async def send_message(
        self,
        content: Optional[str] = None,
        *,
        embeds: Optional[List[Embed]] = None,
        row: Optional[ActionRow] = None,
        **kwargs,
    ) -> Message:

        if self._responded:
            raise TypeError("Responded to this interaction already")

        embeds = [] if embeds is None else embeds

        payload = update_payload(
            {},
            content=content,
            components=[row._to_dict()] if row is not None else None,
            embeds=[embed.to_dict() for embed in embeds],
            **kwargs,
        )

        await self._state.http.create_interaction_response(
            self.id, self.token, type=4, data=payload
        )
        self._responded = True

        data = await self._state.http.get_original_interaction_response(
            self.application_id, self.token
        )
        return self._state.create_message(data, self.channel)

    def _create_user(self) -> Union[User, Member]:
        if (member_data := self._data.get("member")) and self.guild:
            return self._state._create_member(member_data, self.guild)

        return self._state.add_user(self._data["user"])

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Union

from lefi.utils.payload import update_payload

from ..components import ActionRow
from ..embed import Embed
from ..member import Member
from ..enums import InteractionResponse, InteractionType

if TYPE_CHECKING:
    from ..channel import Channel, DMChannel
    from ..guild import Guild
    from ..message import Message
    from ..user import User
    from ...state import State

__all__ = ("Interaction",)


class Interaction:
    """
    An object representing a discord interaction.
    """

    def __init__(self, state: State, data: Dict, type: InteractionType) -> None:
        self._type = type

        self._state = state
        self._data = data

        self._user: Union[User, Member] = None  # type: ignore
        self._origin: Message = None  # type: ignore
        self._responded: bool = False

    @property
    def data(self) -> Dict:
        return self._data["data"]

    @property
    def type(self) -> InteractionType:
        """
        The type of the interaction.
        """
        return self._type

    @property
    def token(self) -> str:
        """
        The token of the interaction. These are only valid for 15 minutes.
        """
        return self._data["token"]

    @property
    def application_id(self) -> int:
        """
        The
        applications id.
        """
        return int(self._data["application_id"])

    @property
    def id(self) -> int:
        """
        The interactions ID
        """
        return int(self._data["id"])

    @property
    def responded(self) -> bool:
        """
        Whether or not the interaction has been responded to.
        """
        return self._responded

    @property
    def channel(self) -> Optional[Union[Channel, DMChannel]]:
        """
        The channel where the interaction was created.
        """
        if self.message is not None:
            return self.message.channel

        if self._data.get("message"):
            return self._state.get_channel(int(self._data["message"]["channel_id"]))

        return self._state.get_channel(int(self._data["channel_id"]))

    @property
    def message(self) -> Optional[Message]:
        """
        The message which invoked the interaction.
        """
        if message_data := self._data.get("message"):
            if message := self._state.get_message(message_data["id"]):
                return message

            channel = self._state.get_channel(int(self._data["message"]["channel_id"]))
            return self._state.create_message(self._data["message"], channel)

        return None

    @property
    def user(self) -> Union[User, Member]:
        """
        The user or member that created the interaction.
        """
        if self._user is None:
            self._user = self._create_user()

        return self._user

    @property
    def guild(self) -> Optional[Guild]:
        """
        The guild where the interaction was created, if in one.
        """

        if self.channel is not None:
            return self.channel.guild

        return self._state.get_guild(int(self._data["guild_id"]))

    @property
    def origin(self) -> Optional[Message]:
        """
        The original response message of the interaction.
        """
        if self._responded and self._origin:
            return self._origin

        return None

    async def send_message(
        self,
        content: Optional[str] = None,
        *,
        embeds: Optional[List[Embed]] = None,
        rows: Optional[List[ActionRow]] = None,
        **kwargs,
    ) -> Message:
        """
        Sends a message through the interaction.

        Parameters:
            content (Optional[str]): The content of the message.
            embeds (Optional[List[Embed]]): The embeds of the message.
            rows (Optional[List[ActionRow]]): The rows to send with the message.
            **kwargs: Extra options to pass.

        Returns:
            The message after it was sent.
        """

        if self._responded:
            raise TypeError("Responded to this interaction already")

        embeds = [] if embeds is None else embeds

        payload = update_payload(
            {},
            content=content,
            components=[row.to_dict() for row in rows] if rows is not None else None,
            embeds=[embed.to_dict() for embed in embeds],
            **kwargs,
        )

        if rows is not None and payload.get("components"):
            for row in rows:
                for component in row.components:
                    self._state._components[component.custom_id] = (
                        component.callback,
                        component,
                    )

        await self._state.http.create_interaction_response(
            self.id, self.token, type=InteractionResponse.MESSAGE, data=payload
        )

        data = await self._state.http.get_original_interaction_response(
            self.application_id, self.token
        )

        self._responded = True
        self._origin = self._state.create_message(data, self.channel)
        return self._origin

    async def edit_origin(
        self,
        content: Optional[str] = None,
        *,
        embeds: Optional[List[Embed]] = None,
        rows: Optional[List[ActionRow]] = None,
        **kwargs,
    ) -> Message:
        """
        Edits the interactions original response message.

        Parameters:
            content (Optional[str]): The content of the message.
            embeds (Optional[List[lefi.Embed]]): The list of embeds.
            rows (Optional[List[ActionRow]]): The rows to send with the message.
            kwargs (Any): The options to pass to [lefi.HTTPClient.edit_message](./http.md#lefi.HTTPClient.edit_message).

        Returns:
            The message after being editted.
        """

        embeds = [] if not embeds else embeds

        payload = update_payload(
            {},
            content=content,
            components=[row.to_dict() for row in rows] if rows is not None else None,
            embeds=[embed.to_dict() for embed in embeds],
        )

        if rows is not None and payload.get("components"):
            for row in rows:
                for component in row.components:
                    self._state._components[component.custom_id] = (
                        component.callback,
                        component,
                    )

        data = await self._state.http.edit_original_interaction_response(
            self.application_id, self.token, **payload
        )
        return self._state.create_message(data, self.channel)

    async def delete_origin(self) -> None:
        """
        Deletes the original response message.
        """
        await self._state.http.delete_original_interaction_response(
            self.application_id, self.token
        )

    async def defer(self) -> None:
        """
        Defers the interaction.
        """
        if self._responded:
            raise TypeError("Responded to this interaction already")

        await self._state.http.create_interaction_response(
            self.id,
            self.token,
            type=int(self.type),
        )
        self._responded = True

    async def pong(self) -> None:
        """
        Responds to a ping.
        """
        if self._responded:
            raise TypeError("Responded to this interaction already")

        await self._state.http.create_interaction_response(
            self.id, self.token, type=InteractionResponse.PONG
        )
        self._responded = True

    async def edit_message(
        self,
        content: Optional[str] = None,
        *,
        embeds: Optional[List[Embed]] = None,
        rows: Optional[List[ActionRow]] = None,
        **kwargs,
    ) -> Message:
        """
        Edits the message invoking the interaction.

        Parameters:
            content (Optional[str]): The content of the message.
            embeds (Optional[List[lefi.Embed]]): The list of embeds.
            rows (Optional[List[ActionRow]]): The rows to send with the message.
            kwargs (Any): The options to pass to [lefi.HTTPClient.edit_message](./http.md#lefi.HTTPClient.edit_message).

        Returns:
            The message after being editted.
        """

        embeds = [] if not embeds else embeds

        payload = update_payload(
            {},
            content=content,
            components=[row.to_dict() for row in rows] if rows is not None else None,
            embeds=[embed.to_dict() for embed in embeds],
        )

        if rows is not None and payload.get("components"):
            for row in rows:
                for component in row.components:
                    self._state._components[component.custom_id] = (
                        component.callback,
                        component,
                    )

        data = await self._state.http.create_interaction_response(
            self.id, self.token, type=InteractionResponse.UPDATE, data=payload
        )

        return self._state.create_message(data, self.channel)

    def _create_user(self) -> Union[User, Member]:
        if (member_data := self._data.get("member")) and self.guild:
            return self._state._create_member(member_data, self.guild)

        return self._state.add_user(self._data["user"])

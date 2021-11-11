from __future__ import annotations
from abc import abstractmethod

from typing import TYPE_CHECKING, Optional, List, ClassVar, Dict, Union

import regex

from lefi.utils.payload import update_payload

from .enums import CommandType, ChannelType, CommandOptionType

if TYPE_CHECKING:
    from .interactions import Interaction
    from ..client import Client

__all__ = (
    "CommandOption",
    "CommandChoice",
    "AppCommand",
)


class CommandChoice:
    def __init__(self, name: str, value: Union[str, float, int]) -> None:
        self.name = name
        self.value = value

    def to_dict(self) -> Dict:
        return {"name": self.name, "value": self.value}


class CommandOption:
    def __init__(self, name: str, description: Optional[str] = None, **kwargs) -> None:
        self.description = description or ""
        self.name = name

        self.required: bool = kwargs.get("required", False)
        self.choices: Optional[List[CommandChoice]] = kwargs.get("choices")
        self.options: Optional[List[CommandOption]] = kwargs.get("options")
        self.type: CommandOptionType = kwargs.get("type", CommandOptionType.STRING)
        self.min_value: Optional[float] = kwargs.get("min_value")
        self.max_value: Optional[float] = kwargs.get("max_value")
        self.channel_types: List[ChannelType] = kwargs.get("channel_types", [])
        self.autocomplete: bool = kwargs.get("autocomplete", False)

    def to_dict(self) -> Dict:
        choices = (
            [choice.to_dict() for choice in self.choices]
            if self.choices is not None
            else []
        )
        options = (
            [opt.to_dict() for opt in self.options] if self.options is not None else []
        )

        channel_types = [int(type_) for type_ in self.channel_types]

        return update_payload(
            {},
            name=self.name,
            description=self.description,
            required=self.required,
            choices=choices,
            options=options,
            type=self.type,
            min_vlaue=self.min_value,
            max_value=self.max_value,
            channel_types=channel_types,
            autocomplete=self.autocomplete,
        )


class AppCommand:
    NAME_REGEX: ClassVar[str] = r"^[\w-]{1,32}$"

    def __init__(self, name: str, description: Optional[str] = None, **kwargs) -> None:
        self.description = description or ""
        self.name = name

        self.client: Client = kwargs["client"]
        self.type: CommandType = kwargs.get("type", CommandType.CHAT)
        self.app_id: int = kwargs.get("app_id", self.client.user.id)
        self.command_id: Optional[int] = kwargs.get("command_id")

        self.options: List[CommandOption] = kwargs.get("options", [])
        self.guild_ids: Optional[List[int]] = kwargs.get("guild_ids")
        self.default_permission: bool = kwargs.get("default_permission", True)

        if self.type is CommandType.CHAT:
            self._validate_names()

    async def callback(self, interaction: Interaction) -> None:
        raise NotImplementedError

    def _validate_names(self) -> None:
        if not regex.findall(self.NAME_REGEX, self.name):
            raise TypeError(f"Name: {self.name} does not match {self.NAME_REGEX}")

        for option in self.options:
            if not regex.findall(self.NAME_REGEX, option.name):
                raise TypeError(
                    f"Option name: {option.name} does not match {self.NAME_REGEX}"
                )

    async def register(self) -> None:
        http = self.client.http
        options = (
            [opt.to_dict() for opt in self.options]
            if self.options is not None
            else None
        )

        if self.guild_ids is None:
            await http.create_global_application_command(
                self.app_id,
                name=self.name,
                description=self.description,
                options=options,
                type=self.type,
                default_permission=self.default_permission,
            )

            return None

        for guild_id in self.guild_ids:
            await http.create_guild_application_command(
                self.app_id,
                guild_id,
                name=self.name,
                description=self.description,
                options=options,
                type=int(self.type),
                default_permission=self.default_permission,
            )

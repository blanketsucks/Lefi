from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    TypeVar,
    Generic,
    ClassVar,
    Type,
    Tuple,
    Dict,
    Union,
    Any,
)

import inspect
import re
import sys

from lefi import Object, User, Member, Guild, Channel, TextChannel, VoiceChannel, CategoryChannel, ChannelType, utils

if TYPE_CHECKING:
    from .context import Context

__all__ = (
    "Converter",
    "ObjectConverter",
    "UserConverter",
    "MemberConverter",
    "GuildConverter",
    "GuildChannelConverter",
    "TextChannelConverter",
    "VoiceChannelConverter",
    "CategoryChannelConverter",
)

T_co = TypeVar("T_co", covariant=True)


class ConverterMeta(type):
    __convert_type__: Type

    def __new__(cls: Type[ConverterMeta], name: str, bases: Tuple[Type, ...], attrs: dict) -> ConverterMeta:
        attrs["__convert_type__"] = attrs["__orig_bases__"][0].__args__[0]
        return super().__new__(cls, name, bases, attrs)


class Converter(Generic[T_co], metaclass=ConverterMeta):
    """A base converter class.
    All converters should inherit this class.
    """

    __convert_type__: Type
    ID_REGEX: ClassVar[re.Pattern] = re.compile(r"([0-9]{15,20})$")
    MENTION_REGEX: ClassVar[re.Pattern] = re.compile(r"<(?:@(?:!|&)?|#)([0-9]{15,20})>$")

    @staticmethod
    async def convert(ctx: Context, data: str) -> T_co:
        """Converts a string into the corresponding type.

        Parameters
        ----------
        ctx: :class:`.Context`
            The invocation context

        data: :class:`str`
            The data to convert into the corresponding type

        Returns
        -------
        :class:`typing.TypeVar`
            The data converted to the corresponding type.
        """
        raise NotImplementedError


class ObjectConverter(Converter[Object]):
    @staticmethod
    async def convert(ctx: Context, data: str) -> Object:
        """Converts the string given into a Object.

        Accepted arguments:
        - id or mention

        Parameters
        ----------
        ctx: :class:`.Context`
            The invocation context

        data: :class:`str`
            The data to convert into a :class:`.Object`

        Raises
        ------
        :exc:`TypeError`
            The data given couldn't be converted.

        Returns
        -------
        :class:`.Object`
            The created Object instance from the data given.
        """
        found = Converter.ID_REGEX.match(data) or Converter.MENTION_REGEX.match(data)

        if found is None:
            raise TypeError(f"{data!r} cannot be converted to Object")

        return Object(id=int(found.group(1)))


class UserConverter(Converter[User]):
    @staticmethod
    async def convert(ctx: Context, data: str) -> User:
        """Converts the string given into a User.

        Accepted arguments:
        - id or mention
        - username and discriminator
        - username

        Parameters
        ----------
        ctx: :class:`.Context`
            The invocation context

        data: :class:`str`
            The data to convert into a :class:`.User`

        Raises
        ------
        :exc:`TypeError`
            The data given couldn't be converted.

        Returns
        -------
        :class:`.User`
            The User instance from the data given.
        """
        found = Converter.ID_REGEX.match(data) or Converter.MENTION_REGEX.match(data)
        bot = ctx.bot

        if found is not None:
            user_id = int(found.group(1))
            user = bot.get_user(user_id) or await bot.fetch_user(user_id)

            if user is None:
                raise TypeError(f"{data!r} cannot be converted to a User")

            return user

        data.removeprefix("@")
        username: str = data[:-5]
        discriminator: str = data[-4:]

        if len(data) > 5 and data[-5] == "#" and discriminator.isdigit():
            if user_ := utils.get(bot.users, username=username, discriminator=int(discriminator)):
                return user_

        if user_ := utils.get(bot.users, username=data):
            return user_

        raise TypeError(f"{data!r} cannot be converted to a User")


class MemberConverter(Converter[Member]):
    @staticmethod
    async def convert(ctx: Context, data: str) -> Member:
        """Converts the string given into a Member.

        Accepted arguments:
        - id or mention
        - username and discriminator
        - username

        Parameters
        ----------
        ctx: :class:`.Context`
            The invocation context

        data: :class:`str`
            The data to convert into a :class:`.Member`

        Raises
        ------
        :exc:`TypeError`
            The data given couldn't be converted.

        Returns
        -------
        :class:`.Member`
            The Member instance from the data given.
        """
        found = Converter.ID_REGEX.match(data) or Converter.MENTION_REGEX.match(data)
        guild = ctx.guild

        if guild is None:
            raise TypeError("Cannot convert {data!r} to a Member inside of DMChannel.")

        if found is not None:
            member_id = int(found.group(1))
            member = guild.get_member(member_id) or await guild.fetch_member(member_id)

            if member is None:
                raise TypeError(f"{data!r} cannot be converted to a Member")

            return member

        data.removeprefix("@")
        username: str = data[:-5]
        discriminator: str = data[-4:]

        if len(data) > 5 and data[-5] == "#" and discriminator.isdigit():
            if member_ := utils.get(guild.members, username=username, discriminator=int(discriminator)):
                return member_

        if member_ := utils.get(guild.members, username=data) or utils.get(guild.members, nick=data):
            return member_

        raise TypeError(f"{data!r} cannot be converted to a Member")


class GuildConverter(Converter[Guild]):
    @staticmethod
    async def convert(ctx: Context, data: str) -> Guild:
        """Converts the string given into a Guild.

        Accepted arguments:
        - name
        - id

        Parameters
        ----------
        ctx: :class:`.Context`
            The invocation context

        data: :class:`str`
            The data to convert into a :class:`.Guild`

        Raises
        ------
        :exc:`TypeError`
            The data given couldn't be converted.

        Returns
        -------
        :class:`.Guild`
            The Guild instance from the data given.
        """
        found = Converter.ID_REGEX.match(data)
        bot = ctx.bot

        if found is not None:
            guild_id = int(found.group(1))
            guild = bot.get_guild(guild_id) or await bot.fetch_guild(guild_id)

            if guild is not None:
                return guild

            raise TypeError(f"{data!r} cannot be converted to Guild")

        if guild_ := utils.get(bot.guilds, name=data):
            return guild_

        raise TypeError(f"{data!r} cannot be converted to Guild")


class GuildChannelConverter(Converter[Channel]):
    @staticmethod
    async def convert(ctx: Context, data: str, *, type: Type[Channel] = Channel) -> Any:
        """Converts the string given into a guild channel.

        Accepted arguments:
        - mention
        - name
        - id

        Parameters
        ----------
        ctx: :class:`.Context`
            The invocation context

        data: :class:`str`
            The data to convert into a channel

        type: Type[:class:`Channel`]
            The type of channel to accept. This is used internally for the
            other channel converters

        Raises
        ------
        :exc:`TypeError`
            The data given couldn't be converted.

        Returns
        -------
        Union[:class:`.Channel`, :class:`.CategoryChannel`]
            The channel instance from the data given.
        """
        found = Converter.ID_REGEX.match(data) or Converter.MENTION_REGEX.match(data)
        guild = ctx.guild

        if guild is None:
            raise TypeError(f"{data!r} cannot be converted to a {type!r} inside of a DMChannel")

        if found is not None:
            channel_id = int(found.group(1))

            if channel := guild.get_channel(channel_id) or await ctx.bot.fetch_channel(channel_id):
                if isinstance(channel, type):
                    return channel

                elif channel.type is ChannelType.CATEGORY and type is CategoryChannel:
                    return channel

        if channel_ := utils.get(guild.channels, name=data):
            if isinstance(channel_, type):
                return channel_

            elif channel_.type is ChannelType.CATEGORY and type is CategoryChannel:
                return channel_

        raise TypeError(f"{data!r} cannot be converted to {type!r}")


class TextChannelConverter(Converter[TextChannel]):
    @staticmethod
    async def convert(ctx: Context, data: str) -> TextChannel:
        """Converts the string given into a text channel.

        Accepted arguments:
        - mention
        - name
        - id

        Parameters
        ----------
        ctx: :class:`.Context`
            The invocation context

        data: :class:`str`
            The data to convert into a channel

        Raises
        ------
        :exc:`TypeError`
            The data given couldn't be converted.

        Returns
        -------
        :class:`.TextChannel`
            The channel instance from the data given.
        """
        return await GuildChannelConverter.convert(ctx, data, type=TextChannel)


class VoiceChannelConverter(Converter[VoiceChannel]):
    @staticmethod
    async def convert(ctx: Context, data: str) -> VoiceChannel:
        """Converts the string given into a voice channel.

        Accepted arguments:
        - mention
        - name
        - id

        Parameters
        ----------
        ctx: :class:`.Context`
            The invocation context

        data: :class:`str`
            The data to convert into a channel

        Raises
        ------
        :exc:`TypeError`
            The data given couldn't be converted.

        Returns
        -------
        :class:`.VoiceChannel`
            The channel instance from the data given.
        """
        return await GuildChannelConverter.convert(ctx, data, type=VoiceChannel)


class CategoryChannelConverter(Converter[CategoryChannel]):
    @staticmethod
    async def convert(ctx: Context, data: str) -> CategoryChannel:
        """Converts the string given into a category channel.

        Accepted arguments:
        - name
        - id

        Parameters
        ----------
        ctx: :class:`.Context`
            The invocation context

        data: :class:`str`
            The data to convert into a channel

        Raises
        ------
        :exc:`TypeError`
            The data given couldn't be converted.

        Returns
        -------
        :class:`.CategoryChannel`
            The channel instance from the data given.
        """
        return await GuildChannelConverter.convert(ctx, data, type=CategoryChannel)  # type: ignore


_CONVERTERS: Dict[str, Union[Type[Converter], Converter]] = {}
for name, object in inspect.getmembers(sys.modules[__name__], inspect.isclass):
    if not issubclass(object, Converter) or name == "Converter":
        continue

    _CONVERTERS[object.__convert_type__.__name__] = object

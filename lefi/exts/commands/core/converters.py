from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    TypeVar,
    Generic,
    ClassVar,
    Optional,
    Type,
    Tuple,
    Dict,
)

import inspect
import re
import sys

from lefi import Snowflake, Object

if TYPE_CHECKING:
    from .context import Context


T_co = TypeVar("T_co", covariant=True)


class ConverterMeta(type):
    __convert_type__: Type

    def __new__(
        cls: Type[ConverterMeta], name: str, bases: Tuple[Type, ...], attrs: dict
    ) -> ConverterMeta:
        attrs["__convert_type__"] = attrs["__orig_bases__"][0].__args__[0]
        return super().__new__(cls, name, bases, attrs)


class Converter(Generic[T_co], metaclass=ConverterMeta):
    __convert_type__: Type
    """A base converter class."""

    @staticmethod
    async def convert(ctx: Context, data: str) -> Optional[T_co]:
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
    ID_REGEX: ClassVar[re.Pattern] = re.compile(r"([0-9]{15,20})$")
    MENTION_REGEX: ClassVar[re.Pattern] = re.compile(r"<(?:@(?:!|&)?|#)([0-9]{15,20})>$")

    @staticmethod
    async def convert(ctx: Context, data: str) -> Optional[Object]:
        """Converts the string given into a Object.

        Parameters
        ----------
        ctx: :class:`.Context`
            The invocation context

        data: :class:`str`
            The data to convert into a :class:`.Object`

        Returns
        -------
        Optional[:class:`.Object`]
            The created Object instance from the data given.
        """
        found = ObjectConverter.ID_REGEX.match(data) or ObjectConverter.MENTION_REGEX.match(data)

        if found is not None:
            return Object(id=int(found.group(1)))

        return None

_CONVERTERS: Dict[str, Type[Converter]] = {}
for name, object in inspect.getmembers(sys.modules[__name__], inspect.isclass):
    if not issubclass(object, Converter) or name == "Converter":
        continue

    _CONVERTERS[object.__convert_type__.__name__] = object

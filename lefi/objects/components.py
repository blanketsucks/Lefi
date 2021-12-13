from __future__ import annotations

import functools
import uuid
from typing import (
    TYPE_CHECKING,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Union,
    Type,
    Tuple,
)

from ..utils.payload import update_payload
from .enums import ButtonStyle, ComponentType

if TYPE_CHECKING:
    from .emoji import Emoji
    from .interactions import Interaction
    from ..state import State

__all__ = (
    "ActionRow",
    "Component",
    "Button",
    "SelectMenu",
    "Option",
    "button",
)


class Component:
    """Represents a message component.

    .. note::

        This is just a base class.

    Attributes
    ----------
    callback: Callable
        The callback of the component

    custom_id: :class:`str`
        The custom id of the callback
    """

    callback: Callable
    custom_id: str

    def to_dict(self) -> Dict:
        """Creates a payload representing the component."""
        raise NotImplementedError


class Button(Component):
    """Represents a button component.

    Parameters
    ----------
    style: :class:`ButtonStyle`
        The style of button to create

    label: :class:`str`
        The label of the button

    custom_id: Optional[:class:`str`]
        The custom id to set for the button

    disabled: Optional[:class:`bool`]
        Whether or not the button should be marked as disabled

    emoji: Optional[:class:`.Emoji`]
        The emoji to set for the button

    url: Optional[:class:`str`]
        The url to use for url styled buttons

    Attributes
    ----------
    style: :class:`.ButtonStyle`
        The style of the button

    label: :class:`str`
        The label of the button

    custom_id: :class:`str`
        The custom id of the button

    disabled: :class:`bool`
        If the button is disabled or not

    emoji: Optional[Union[:class:`str`, :class:`.Emoji`]]
        The emoji of the button

    url Optional[:class:`str`]
        The url of the button
    """

    def __init__(self, style: ButtonStyle, label: str, **kwargs) -> None:
        self.style: ButtonStyle = style
        self.label: str = label

        self.custom_id: str = kwargs.get("custom_id", uuid.uuid4().hex)
        self.disabled: bool = kwargs.get("disabled", False)
        self.emoji: Optional[Emoji] = kwargs.get("emoji")
        self.url: Optional[str] = kwargs.get("url")

    async def callback(self, interaction: Interaction, button: Button) -> None:
        """The button's callback.

        This is ran everytime the button is pressed. By default this does nothing and
        requires the user to override this method in order for an action to be done.

        Parameters
        ----------
        interaction: :class:`.Interaction`
            The interaction which "activated" the button

        button: :class:`.Button`
            The button which was pressed
        """
        raise NotImplementedError

    def to_dict(self) -> dict:
        """Creates a dict from the button.

        Returns
        -------
        :class:`dict`
            The dict representing the button.
        """
        payload = {
            "style": int(self.style),
            "type": int(ComponentType.BUTTON),
            "custom_id": self.custom_id,
            "label": self.label,
        }

        emoji = None
        if self.emoji is not None:
            if isinstance(self.emoji, Emoji):
                emoji = {"name": self.emoji.name, "id": self.emoji.id}

            elif isinstance(self.emoji, str):
                emoji = {"name": self.emoji}

        return update_payload(
            payload,
            emoji=emoji,
            custom_id=self.custom_id,
            url=self.url,
            disabled=self.disabled,
        )


class Option:
    """Represents an option for a select menu.

    Parameters
    ----------
    label: :class:`str`
        The label of the option

    value: :class:`str`
        The value of the option

    description: Optional[:class:`str`]
        The description for the option

    emoji: Optional[Union[:class:`str`, :class:`.Emoji`]]
        The emoji for this option

    default: Optional[:class:`bool`]
        Whether or not this option should be selected by default

    Attributes
    ----------
    label: :class:`str`
        The label of the option

    value: :class:`str`
        The value of the option

    description: Optional[:class:`str`]
        The description of the option

    emoji: Optional[Union[:class:`str`, :class:`.Emoji`]]
        The emoji of the option

    default: :class:`bool`
        Whether or not the option is the default
    """

    def __init__(self, label: str, value: str, **kwargs) -> None:
        self.label = label
        self.value = value

        self.description: Optional[str] = kwargs.get("description")
        self.emoji: Optional[Union[str, Emoji]] = kwargs.get("emoji")
        self.default: bool = kwargs.get("default", False)

    def to_dict(self) -> dict:
        """Creates a dict from the option.

        Returns
        -------
        :class:`dict`
            The dict representing the option.
        """
        emoji = None
        if self.emoji is not None:
            if isinstance(self.emoji, Emoji):
                emoji = {"name": self.emoji.name, "id": self.emoji.id}

            elif isinstance(self.emoji, str):
                emoji = {"name": self.emoji}

        return update_payload(
            {},
            label=self.label,
            value=self.value,
            description=self.description,
            emoji=emoji,
            default=self.default,
        )


class SelectMenu(Component):
    """Represents a select menu.

    Parameters
    ----------
    options: List[:class:`.Option`]
        A list of options for the select menu

    custom_id: Optional[:class:`str`]
        The custom id to give the select menu

    placeholder: Optional[:class:`str`]
        The placeholder of the select menu

    min_values: Optional[:class:`int`]
        The minimum values required to select

    max_values: Optional[:class:`int`]
        The max amount of values that can be selected

    disabled: Optional[:class:`bool`]
        Whether or not the select menu should be marked as disabled

    Attributes
    ----------
    options: List[:class:`.Option`]
        A list of options connected to the select menu

    custom_id: :class:`str`
        The custom id of the select menu

    min_values: :class:`int`
        The minimum values needed to be selected for the select menu

    max_values: :class:`int`
        The max amount of values that can be selected

    disabled: :class:`bool`
        Whether or not the select menu is disabled

    values: List[:class:`str`]
        A list of values selected. This is only set if the select menu
        was used beforehand
    """

    def __init__(self, options: List[Option], **kwargs) -> None:
        self.options = options

        self.custom_id: str = kwargs.get("custom_id", uuid.uuid4().hex)
        self.placeholder: Optional[str] = kwargs.get("placeholder")
        self.min_values: int = kwargs.get("min_values", 1)
        self.max_values: int = kwargs.get("max_values", 1)
        self.disabled: bool = kwargs.get("disabled", False)

        self.values: List[str] = []

    async def callback(self, interaction: Interaction, menu: SelectMenu) -> None:
        """The select menu's callback.

        This is ran everytime the select menu is used. By default this does nothing and
        requires the user to override this method in order for an action to be done.

        Parameters
        ----------
        interaction: :class:`.Interaction`
            The interaction which "activated" the select menu

        menu: :class:`.SelectMenu`
            The select menu which was used
        """
        raise NotImplementedError

    def to_dict(self) -> dict:
        """Creates a dict from the select menu.

        Returns
        -------
        :class:`dict`
            The dict representing the select menu.
        """

        return update_payload(
            {},
            type=int(ComponentType.SELECTMENU),
            placeholder=self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            options=[option.to_dict() for option in self.options],
            disabled=self.disabled,
            custom_id=self.custom_id,
        )


class ActionRowMeta(type):
    __components__: List[Component]

    def __new__(cls: Type[ActionRowMeta], name: str, bases: Tuple[Type, ...], attrs: Dict) -> ActionRowMeta:
        components: List[Component] = []

        for value in attrs.copy().values():
            if isinstance(value, Component):
                components.append(value)

        attrs["__components__"] = components
        return super().__new__(cls, name, bases, attrs)


class ActionRow(Component, metaclass=ActionRowMeta):
    """Represents a message action row.

    Parameters
    ----------
    components: Optional[List[:class:`.Component`]]
        A list of components connected to the action row
    """

    __components__: List[Component]

    def __init__(self, components: Optional[List[Component]] = None) -> None:
        if components is not None:
            self.__components__.extend(components)

    @property
    def components(self) -> List[Component]:
        """The components which are connected to the action row."""
        return self.__components__

    def add(self, component: Component) -> None:
        """Add a component to the action row.

        Parameters
        ----------
        component: :class:`Component`
            The component to add
        """
        self.components.append(component)

    def to_dict(self) -> dict:
        """Creates a dict from the action row.

        Returns
        -------
        :class:`dict`
            The dict representing the action row.
        """
        return {
            "type": int(ComponentType.ACTIONROW),
            "components": [c.to_dict() for c in self.components],
        }

    def _cache_components(self, state: State) -> None:
        for component in self.components:
            state._components[component.custom_id] = (component.callback, component)


def button(style: ButtonStyle, label: str, **kwargs) -> Callable[..., Button]:
    """A decorator used to create buttons.

    This should be decorating the buttons callback.

    Parameters
    ----------
    style: :class:`.ButtonStyle`
        The styling to use for the button

    label: :class:`str`
        The label of the button

    custom_id: Optional[:class:`str`]
        The custom id to set for the button

    disabled: Optional[:class:`bool`]
        Whether or not the button should be marked as disabled

    emoji: Optional[:class:`.Emoji`]
        The emoji to set for the button

    url: Optional[:class:`str`]
        The url to use for url styled buttons

    Returns
    -------
    :class:`.Button`
        The created button instance
    """

    def inner(func: Coroutine) -> Button:
        button = Button(style, label, **kwargs)
        button.callback = functools.partial(func, button)  # type: ignore

        return button

    return inner

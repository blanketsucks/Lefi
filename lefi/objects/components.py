from __future__ import annotations

import enum
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

__all__ = (
    "ActionRow",
    "Component",
    "Button",
    "SelectMenu",
    "Option",
    "button",
)


class Component:
    """
    Represents a message component.
    """

    callback: Callable
    custom_id: str

    def to_dict(self) -> Dict:
        raise NotImplementedError


class Button(Component):
    """
    Represents a button component.

    Attributes:
        style (ComponentStyle): The style of the button.
        label (str): The button's label.
        custom_id (str): The buttons custom_id.
        disabled (bool): Whether the button is disabled or not.
        emoji (Optional[str]): The emoji to use for the button.
        url (Optional[str]): The url of the button
        callback (Coroutine): The coroutine to run after the button is pressed.

    """

    def __init__(self, style: ButtonStyle, label: str, **kwargs) -> None:
        """
        Parameters:
            style (ComponentStyle): The style to use.
            label (str): The label to use.
            callback (Coroutine): The callback to use.

        """
        self.style: ButtonStyle = style
        self.label: str = label

        self.custom_id: str = kwargs.get("custom_id", uuid.uuid4().hex)
        self.disabled: bool = kwargs.get("disabled", False)
        self.emoji: Optional[Emoji] = kwargs.get("emoji")
        self.url: Optional[str] = kwargs.get("url")

    async def callback(self, interaction: Interaction, button: Component) -> None:
        raise NotImplementedError

    def to_dict(self) -> Dict:
        payload = {
            "style": int(self.style),
            "type": int(ComponentType.BUTTON),
            "custom_id": self.custom_id,
            "label": self.label,
        }

        return update_payload(
            payload,
            emoji=self.emoji,
            custom_id=self.custom_id,
            url=self.url,
            disabled=self.disabled,
        )


class Option:
    """
    Represents an option for a select menu.

    Attributes:
        label (str): The label of the option.
        value (str): The value of the option.
        description (Optional[str]): The description.
        emoji (Optional[Union[str, Emoji]]): The emoji for the option.
        default (bool): Whether or not the option is the default option.

    """

    def __init__(self, label: str, value: str, **kwargs) -> None:
        """
        Parameters:
            label (str): The label of the option.
            value (str): The value of the option.
            description (Optional[str]): The description.
            emoji (Optional[Union[str, Emoji]]): The emoji for the option.
            default (bool): Whether or not the option is the default option.

        """
        self.label = label
        self.value = value

        self.description: Optional[str] = kwargs.get("description")
        self.emoji: Optional[Union[str, Emoji]] = kwargs.get("emoji")
        self.default: bool = kwargs.get("default", False)

    def to_dict(self) -> Dict:
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
    """
    Represents a discord select menu.

    Attributes:
        custom_id (str): The custom id of the select menu.
        placeholder (Optional[str]): The placeholder of the select menu.
        min_values (int): The minimum amount of values that can be choosen.
        max_values (int): The maximum amount of values that can be choosen.
        disabled (bool): Whether or not the select menu is disabled.
        values (List[str]): The list of values choosen after an interaction happens.

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
        raise NotImplementedError

    def to_dict(self) -> Dict:
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

    def __new__(
        cls: Type[ActionRowMeta], name: str, bases: Tuple[Type, ...], attrs: Dict
    ) -> ActionRowMeta:
        components: List[Component] = []

        for value in attrs.copy().values():
            if isinstance(value, Component):
                components.append(value)

        attrs["__components__"] = components
        return super().__new__(cls, name, bases, attrs)


class ActionRow(Component, metaclass=ActionRowMeta):
    __components__: List[Component]

    """
    Represents a message action row.

    Attributes:
        components (List[Component]): A list of components connected to the action row.
        callbacks (List[Callable]): A list of callbacks for each child component of the row.

    """

    def __init__(self, components: Optional[List[Component]] = None) -> None:
        """
        Parameters:
            components (List[Component]): The list of components connected to the action row.

        """

        if components is not None:
            self.__components__.extend(components)

    @property
    def components(self) -> List[Component]:
        return self.__components__

    def add(self, component: Component) -> None:
        """
        Add a component to the action row.

        Parameters:
            component (Component): The component to add.

        """
        self.components.append(component)

    def to_dict(self) -> Dict:
        return {
            "type": int(ComponentType.ACTIONROW),
            "components": [c.to_dict() for c in self.components],
        }


def button(style: ButtonStyle, label: str, **kwargs) -> Callable[..., Button]:
    """
    A decorator used to create buttons.
    This should be decorating the buttons callback.

    Parameters:
        style (ComponentStyle): The style of the button.
        label (str): The label of the button.
        **kwargs: Extra options to give to the button.

    Returns:
        The created Button instance.

    """

    def inner(func: Coroutine) -> Button:
        button = Button(style, label, **kwargs)
        button.callback = functools.partial(func, button)  # type: ignore

        return button

    return inner

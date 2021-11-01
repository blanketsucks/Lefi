from __future__ import annotations

import enum
import uuid

from typing import List, Dict, Optional, Coroutine

from .enums import ComponentStyle, ComponentType
from ..utils.payload import update_payload

__all__ = (
    "MessageActionRow",
    "Component",
    "Button",
)


class Component:
    """
    Represents a message component.
    """

    def _to_dict(self) -> Dict:
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

    def __init__(
        self, style: ComponentStyle, label: str, callback: Coroutine, **kwargs
    ) -> None:
        """
        Parameters:
            style (ComponentStyle): The style to use.
            label (str): The label to use.
            callback (Coroutine): The callback to use.

        """
        self.style: ComponentStyle = style
        self.label: str = label

        self.custom_id: str = kwargs.get("custom_id", uuid.uuid4().hex)
        self.disabled: bool = kwargs.get("disabled", False)
        self.emoji: Optional[str] = kwargs.get("emoji")
        self.url: Optional[str] = kwargs.get("url")

        self.callback: Coroutine = callback

    def _to_dict(self) -> Dict:
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


class MessageActionRow(Component):
    """
    Represents a message action row.

    Attributes:
        components (List[Component]): A list of components connected to the action row.

    """

    def __init__(self, components: List[Component]) -> None:
        """
        Parameters:
            components (List[Component]): The list of components connected to the action row.

        """
        self.components = components

    def add(self, component: Component) -> None:
        """
        Add a component to the action row.

        Parameters:
            component (Component): The component to add.

        """
        self.components.append(component)

    def _to_dict(self) -> Dict:
        return {
            "type": int(ComponentType.ACTIONROW),
            "components": [c._to_dict() for c in self.components],
        }

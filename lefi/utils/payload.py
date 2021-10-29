from __future__ import annotations

from typing import Any, Dict

__all__ = ("update_payload",)


def update_payload(payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """
    Update the payload with the given kwargs.

    Parameters:
        payload (dict): The payload to update.
        kwargs (dict): The kwargs to update the payload with.

    Returns:
        The updated payload as a dict.
    """
    for key, value in kwargs.items():
        if value is not None:
            payload[key] = value

    return payload

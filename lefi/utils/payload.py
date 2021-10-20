from __future__ import annotations

from typing import Any, Dict

__all__ = ("update_payload",)


def update_payload(payload: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    for key, value in kwargs.items():
        if value is not None:
            payload[key] = value

    return payload

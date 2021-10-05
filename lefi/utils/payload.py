from typing import Dict, Any

from .missing import MISSING

__all__ = ('update_payload',)

def update_payload(payload: Dict[str, Any], **kwargs: Any):
    for key, value in kwargs.items():
        if value is not MISSING:
            payload[key] = value

    return payload
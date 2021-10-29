from __future__ import annotations

from typing import Iterable, Callable, TypeVar, List, Union, Optional

T = TypeVar("T")


def find(
    iterable: Iterable[T], check: Callable[[T], bool]
) -> Optional[Union[T, List[T]]]:
    """
    Finds the item in the iterable that matches the check.

    Parameters:
        iterable: The iterable to search on.
        check: The check to use for filtering.

    Returns:
        The item (or a list of items) that match the check.
    """
    found = [item for item in iterable if check(item)]
    return found[0] if len(found) == 1 else found


def get(iterable: Iterable[T], **attrs) -> Optional[T]:
    """
    Finds the item in the iterable that matches the attributes.

    Parameters:
        iterable: The iterable to search on.
        attrs: The attributes to look for.

    Returns:
        The attributes found.
    """
    for item in iterable:
        if all([getattr(item, name) == value for name, value in attrs.items()]):
            return item

    return None

from __future__ import annotations

from typing import Iterable, Callable, TypeVar, List, Union, Optional

T = TypeVar("T")


def find(
    iterable: Iterable[T], check: Callable[[T], bool]
) -> Optional[Union[T, List[T]]]:
    found = [item for item in iterable if check(item)]
    return found[0] if len(found) == 1 else found


def get(iterable: Iterable[T], **attrs) -> Optional[T]:
    for item in iterable:
        if all([getattr(item, name) == value for name, value in attrs.items()]):
            return item

    return None

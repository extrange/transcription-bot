from collections.abc import Callable
from typing import Any, Concatenate


def apply_recursively[T](
    f: Callable[Concatenate[T, ...], Any],
    obj: dict[str, Any] | list,
    criteria: Callable[[T], bool],
) -> None:
    """
    Recursively apply a function to values in a dictionary which satisfy the criteria.

    Recursively includes dicts/lists within lists.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, dict):
                apply_recursively(f, obj[k], criteria)
            elif isinstance(v, list):
                apply_recursively(f, v, criteria)
            # Only apply criteria at the end, in case the criteria itself looks for dicts or lists.
            elif criteria(v):
                obj[k] = f(v)
    else:  # obj is a list
        for v in obj:
            # Also check for dicts/lists within lists
            if isinstance(v, dict | list):
                apply_recursively(f, v, criteria)

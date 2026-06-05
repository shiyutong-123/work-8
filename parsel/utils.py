from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Callable, Type, cast

from w3lib.html import replace_entities as w3lib_replace_entities

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


class MultiDispatch:
    """Multiple dispatch registry using type lookup tables instead of isinstance checks."""

    def __init__(self) -> None:
        self._registry: dict[type, Callable[..., Any]] = {}
        self._fallback: Callable[..., Any] | None = None

    def register(self, type_: type) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            self._registry[type_] = func
            return func
        return decorator

    def set_fallback(self, func: Callable[..., Any]) -> None:
        self._fallback = func

    def dispatch(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        handler = self._registry.get(type(value))
        if handler is not None:
            return handler(value, *args, **kwargs)
        if self._fallback is not None:
            return self._fallback(value, *args, **kwargs)
        raise TypeError(f"No handler registered for type {type(value).__name__}")

    def __call__(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        return self.dispatch(value, *args, **kwargs)


is_listlike_dispatch = MultiDispatch()


@is_listlike_dispatch.register(str)
def _is_listlike_str(value: str) -> bool:
    return False


@is_listlike_dispatch.register(bytes)
def _is_listlike_bytes(value: bytes) -> bool:
    return False


@is_listlike_dispatch.register(bytearray)
def _is_listlike_bytearray(value: bytearray) -> bool:
    return False


def _is_listlike_fallback(value: Any) -> bool:
    return hasattr(value, "__iter__")


is_listlike_dispatch.set_fallback(_is_listlike_fallback)


regex_extract_dispatch = MultiDispatch()


@regex_extract_dispatch.register(str)
def _extract_regex_str(regex: re.Pattern[str], text: str, replace_entities: bool) -> list[str]:
    return _do_extract_regex(regex, text, replace_entities)


@regex_extract_dispatch.register(re.Pattern)
def _extract_regex_pattern(regex: re.Pattern[str], text: str, replace_entities: bool) -> list[str]:
    return _do_extract_regex(regex, text, replace_entities)


def _do_extract_regex(regex: re.Pattern[str], text: str, replace_entities: bool) -> list[str]:
    if "extract" in regex.groupindex:
        try:
            extracted = cast("re.Match[str]", regex.search(text)).group("extract")
        except AttributeError:
            strings = []
        else:
            strings = [extracted] if extracted is not None else []
    else:
        strings = regex.findall(text)

    strings = flatten(strings)
    if not replace_entities:
        return strings
    return [w3lib_replace_entities(s, keep=["lt", "amp"]) for s in strings]


def flatten(x: Iterable[Any]) -> list[Any]:
    """flatten(sequence) -> list
    Returns a single, flat list which contains all elements retrieved
    from the sequence and all recursively contained sub-sequences
    (iterables).
    Examples:
    >>> [1, 2, [3,4], (5,6)]
    [1, 2, [3, 4], (5, 6)]
    >>> flatten([[[1,2,3], (42,None)], [4,5], [6], 7, (8,9,10)])
    [1, 2, 3, 42, None, 4, 5, 6, 7, 8, 9, 10]
    >>> flatten(["foo", "bar"])
    ['foo', 'bar']
    >>> flatten(["foo", ["baz", 42], "bar"])
    ['foo', 'baz', 42, 'bar']
    """
    return list(iflatten(x))


def iflatten(x: Iterable[Any]) -> Iterator[Any]:
    """iflatten(sequence) -> Iterator
    Similar to ``.flatten()``, but returns iterator instead
    Examples:
    >>> list(iflatten([[1, 2], (3, 4)]))
    [1, 2, 3, 4]
    """
    for el in x:
        if is_listlike_dispatch(el):
            yield from flatten(el)
        else:
            yield el


def extract_regex(
    regex: str | re.Pattern[str], text: str, replace_entities: bool = True
) -> list[str]:
    """Extract a list of strings from the given text/encoding using the following policies:
    * if the regex contains a named group called "extract" that will be returned
    * if the regex contains multiple numbered groups, all those will be returned (flattened)
    * if the regex doesn't contain any group the entire regex matching is returned
    """
    if type(regex) is str:
        regex = re.compile(regex, re.UNICODE)

    return regex_extract_dispatch(regex, text, replace_entities)


def shorten(text: str, width: int, suffix: str = "...") -> str:
    """Truncate the given text to fit in the given width."""
    if len(text) <= width:
        return text
    if width > len(suffix):
        return text[: width - len(suffix)] + suffix
    if width >= 0:
        return suffix[len(suffix) - width :]
    raise ValueError("width must be equal or greater than 0")

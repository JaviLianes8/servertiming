"""The error raised for a value that cannot be built or does not follow the grammar."""

from __future__ import annotations

_SHOWN = 60


class ServerTimingError(ValueError):
    """A metric cannot be serialized, or a header breaks the grammar in strict mode.

    ``position`` is the offset of the first offending character in the field value and
    ``field`` the index of that value among those passed to ``parse``; both are ``None``
    when the error is about a value being built rather than parsed. Messages quote at
    most a short excerpt of the input, never the whole of it.

    >>> from timingheader import ServerTimingError, parse
    >>> try:
    ...     parse(["db;dur=1", "cache;dur=fast"], strict=True)
    ... except ServerTimingError as error:
    ...     print(error.field, error.position, isinstance(error, ValueError))
    ...     print(error)
    1 10 True
    dur is not a valid floating-point number at position 10 (found 'f')
    """

    def __init__(self, message: str, position: int | None = None, field: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.position = position
        self.field = field

    def __reduce__(self) -> tuple[type[ServerTimingError], tuple[str, int | None, int | None]]:
        return (type(self), (self.message, self.position, self.field))


def shown(value: object) -> str:
    """``repr(value)`` cut to a short excerpt, safe for any object in an error message."""
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) >= 10**_SHOWN:
        # repr of a huge int is slow and can raise past the digit limit.
        return f"an int of {value.bit_length()} bits"
    try:
        text = repr(value)
    except Exception:
        return f"a {type(value).__name__} that cannot be shown"
    return text if len(text) <= _SHOWN else f"{text[: _SHOWN - 15]}... ({len(text)} chars)"

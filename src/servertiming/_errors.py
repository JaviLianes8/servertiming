"""The error raised for a value that cannot be built or does not follow the grammar."""

from __future__ import annotations


class ServerTimingError(ValueError):
    """A metric cannot be serialized, or a header breaks the grammar in strict mode.

    ``position`` is the offset of the first offending character in the field value and
    ``field`` the index of that value among those passed to ``parse``; both are ``None``
    when the error is about a value being built rather than parsed.
    """

    def __init__(self, message: str, position: int | None = None, field: int | None = None):
        super().__init__(message)
        self.message = message
        self.position = position
        self.field = field

    def __reduce__(self) -> tuple[type[ServerTimingError], tuple[str, int | None, int | None]]:
        return (type(self), (self.message, self.position, self.field))

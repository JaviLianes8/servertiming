"""Character classes from RFC 9110 and the quoting rules built on them."""

from __future__ import annotations

from ._errors import ServerTimingError, shown

# RFC 9110 5.6.2: tchar, any visible US-ASCII character except the delimiters.
TCHARS = frozenset("!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")

# RFC 9110 5.6.3: OWS is spaces and horizontal tabs only.
OWS = frozenset(" \t")

# Names compare without regard to ASCII case only: str.lower would turn the Kelvin sign
# into a "k" and so make a name that is not a token look like one.
_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def ascii_lower(text: str) -> str:
    """``text`` with A to Z lowered and every other character unchanged."""
    return text.translate(_ASCII_LOWER)


def is_token(text: str) -> bool:
    """Whether ``text`` is a non-empty RFC 9110 token."""
    return bool(text) and all(char in TCHARS for char in text)


def is_quotable(char: str) -> bool:
    """Whether ``char`` can appear in a quoted-string, directly or as a quoted-pair.

    RFC 9110 5.6.4 allows HTAB, SP, the visible ASCII characters and obs-text (0x80-0xFF);
    every other control character, DEL and anything a single octet cannot carry is out.
    """
    code = ord(char)
    return code == 0x09 or 0x20 <= code <= 0x7E or 0x80 <= code <= 0xFF


def plain(text: str) -> str:
    """``text`` as an exact ``str``.

    A subclass can change what iterating or formatting it shows while its real characters
    are what gets written, so every check and every write works on the plain copy.
    """
    return str.__str__(text)


def quote(text: str, what: str) -> str:
    """Write ``text`` as a token when it is one, else as an escaped quoted-string."""
    text = plain(text)
    if is_token(text):
        return text
    for index, char in enumerate(text):
        if not is_quotable(char):
            raise ServerTimingError(
                f"{what} holds {char!r} at index {index}, which no HTTP field value can carry"
            )
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def check_token(text: str, what: str) -> str:
    """Return ``text`` as a plain ``str``, or raise when it is not a token."""
    if not isinstance(text, str):
        raise TypeError(f"{what} must be a str, got {shown(text)}")
    text = plain(text)
    if not is_token(text):
        raise ServerTimingError(f"{what} must be a non-empty token, got {shown(text)}")
    return text

"""Durations: the HTML number rules for reading them, and a compact form for writing them."""

from __future__ import annotations

import math
import re

from ._errors import ServerTimingError

# HTML 2.3.4.3, "valid floating-point number": what a sender may write.
_VALID = re.compile(r"-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?")
_DIGITS = re.compile(r"[0-9]*")
_HTML_WHITESPACE = " \t\n\f\r"


def is_valid_number(text: str) -> bool:
    """Whether ``text`` is an HTML valid floating-point number that stays finite."""
    return _VALID.fullmatch(text) is not None and math.isfinite(float(text))


def parse_number(text: str) -> float | None:
    """Read ``text`` with the HTML rules for parsing floating-point number values.

    Returns ``None`` where those rules return an error. Leading whitespace is skipped,
    a leading ``+`` is ignored, anything after the number is ignored, ``-0`` reads as
    ``0`` and a value too large for a double is an error.
    """
    position = len(text) - len(text.lstrip(_HTML_WHITESPACE))
    sign = ""
    if text[position : position + 1] in ("-", "+"):
        sign = "-" if text[position] == "-" else ""
        position += 1
    integer = _digits(text, position)
    position += len(integer)
    fraction = ""
    if text[position : position + 1] == ".":
        fraction = _digits(text, position + 1)
        if fraction or (integer and text[position + 1 : position + 2] in ("e", "E")):
            position += 1 + len(fraction)
    if not integer and not fraction:
        return None
    exponent = ""
    if text[position : position + 1] in ("e", "E"):
        position += 1
        exp_sign = ""
        if text[position : position + 1] in ("-", "+"):
            exp_sign = text[position]
            position += 1
        exp_digits = _digits(text, position)
        if exp_digits:
            exponent = f"e{exp_sign}{exp_digits}"
    # float() rounds a decimal string to the nearest double exactly once, as HTML asks.
    value = float(f"{sign}{integer or '0'}.{fraction or '0'}{exponent}")
    if math.isinf(value):
        return None
    return value + 0.0  # turns -0.0 into 0.0: the HTML set of results has no negative zero


def format_number(value: float, precision: int | None = None) -> str:
    """Write a finite duration compactly: ``12.5``, ``100``, ``1e-05``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ServerTimingError(f"duration must be a real number, got {value!r}")
    try:
        number = float(value)
    except OverflowError:
        number = math.inf
    if not math.isfinite(number):
        raise ServerTimingError(f"duration must be a finite number, got {value!r}")
    if precision is None:
        text = repr(number)
    else:
        text = f"{number:.{precision}f}"
        if "." in text:
            text = text.rstrip("0")
    text = text.removesuffix(".0").removesuffix(".")
    return "0" if text == "-0" else text


def _digits(text: str, position: int) -> str:
    match = _DIGITS.match(text, position)
    return match.group(0) if match else ""

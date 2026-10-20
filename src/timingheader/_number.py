"""Durations: the HTML number rules for reading them, and a compact form for writing them."""

from __future__ import annotations

import math
import re

from ._errors import ServerTimingError, shown

# HTML 2.3.4.3, "valid floating-point number": what a sender may write.
_VALID = re.compile(r"-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?")
_DIGITS = re.compile(r"[0-9]*")
_HTML_WHITESPACE = " \t\n\f\r"
_EXPONENT = re.compile(r"e\+?(-?)0*([0-9])")


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
        # "1." and "1.e5" are numbers too: HTML moves past the dot even with no digits.
        fraction = _digits(text, position + 1)
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
    """Write a finite duration with the shortest digits that read back as the same double.

    The digits and the choice of notation are Python's ``repr``; an exponent is written
    without a plus sign or leading zeros: ``12.5``, ``100``, ``1e-5``, ``1e16``.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"duration must be an int or a float, got {shown(value)}")
    try:
        number = float(value)
    except OverflowError:
        number = math.inf
    if not math.isfinite(number):
        raise ServerTimingError(f"duration must be a finite number, got {shown(value)}")
    if precision is None:
        # repr gives the shortest digits that read back as the same double, but its exponent
        # has a "+" and a leading zero the number does not need ("1e+16", "1e-05").
        text = _EXPONENT.sub(r"e\1\2", repr(number))
    else:
        text = f"{number:.{precision}f}"
        if "." in text:
            text = text.rstrip("0")
    text = text.removesuffix(".0").removesuffix(".")
    return "0" if text == "-0" else text


def _digits(text: str, position: int) -> str:
    match = _DIGITS.match(text, position)
    return match.group(0) if match else ""

"""Durations against the WHATWG HTML number rules, read from the fetched source.

The definition of a valid floating-point number and the rules for parsing floating-point
number values are located in the fetched HTML source (URL and sha256 in
tests/upstream/MANIFEST.json, fetched 2026-10-20). ``_reference`` below is an
independent transcription of those steps, written by hand from that text in exact
rational arithmetic, step by step; it shares no code with the library. The two are
compared on every string of up to four characters over the characters the steps look at,
and on seeded longer strings.
"""

from __future__ import annotations

import itertools
import random
from fractions import Fraction

import pytest
from conftest import prose, upstream_document

from timingheader import Metric, ServerTimingError, parse
from timingheader._number import is_valid_number, parse_number

ALPHABET = " \t\n+-.019eEx"
DIGITS = "0123456789"
MINUS = chr(0x2212)  # the spec writes negative numbers with U+2212


@pytest.fixture(scope="module")
def html_rules() -> str:
    source = upstream_document("whatwg-html-source.html")
    start = source.index("A string is a <dfn>valid floating-point number</dfn>")
    end = source.index("<var>rounded-value</var> is 2<sup>1024</sup>", start)
    return prose(source[start : end + 400])


def _reference(text: str) -> float | None:
    """The rules for parsing floating-point number values, one step per block."""
    pos, value, divisor, exponent = 0, Fraction(1), Fraction(1), 1
    while pos < len(text) and text[pos] in "\t\n\f\r ":  # skip ASCII whitespace
        pos += 1
    if pos >= len(text):
        return None
    if text[pos] == "-":
        value = divisor = Fraction(-1)
        pos += 1
        if pos >= len(text):
            return None
    elif text[pos] == "+":
        pos += 1
        if pos >= len(text):
            return None
    fraction_now = False
    if text[pos] == "." and pos + 1 < len(text) and text[pos + 1] in DIGITS:
        value, fraction_now = Fraction(0), True
    elif text[pos] not in DIGITS:
        return None
    if not fraction_now:
        start = pos
        while pos < len(text) and text[pos] in DIGITS:
            pos += 1
        value *= int(text[start:pos])
        if pos >= len(text):
            return _convert(value)
    if text[pos] == ".":  # the step labeled fraction
        pos += 1
        if pos >= len(text) or text[pos] not in DIGITS + "eE":
            return _convert(value)
        while text[pos] in DIGITS:
            divisor *= 10
            value += Fraction(int(text[pos])) / divisor
            pos += 1
            if pos >= len(text):
                return _convert(value)
    if text[pos] in "eE":
        pos += 1
        if pos >= len(text):
            return _convert(value)
        if text[pos] in "-+":
            exponent = -1 if text[pos] == "-" else 1
            pos += 1
            if pos >= len(text):
                return _convert(value)
        if text[pos] not in DIGITS:
            return _convert(value)
        start = pos
        while pos < len(text) and text[pos] in DIGITS:
            pos += 1
        power = exponent * int(text[start:pos])
        # Past these bounds the exact value is certain to overflow or to round to zero, so
        # the huge power need not be built (the significand here has at most 200 digits).
        if value and power > 1000:
            return None
        if power < -1000:
            return 0.0
        value *= Fraction(10) ** power
    return _convert(value)


def _convert(value: Fraction) -> float | None:
    """The step labeled conversion: nearest double, no negative zero, 2**1024 an error."""
    try:
        rounded = float(value)
    except OverflowError:
        return None
    return rounded + 0.0


def _digits(text: str) -> bool:
    return bool(text) and all(char in DIGITS for char in text)


def _valid_reference(text: str) -> bool:
    """The definition of a valid floating-point number, part by part."""
    rest = text[1:] if text[:1] == "-" else text
    marks = [index for index, char in enumerate(rest) if char in "eE"]
    mantissa = rest[: marks[0]] if marks else rest
    whole, dot, fraction = mantissa.partition(".")
    if not (
        (_digits(whole) and not dot)
        or ((_digits(whole) or not whole) and dot and _digits(fraction))
    ):
        return False
    if not marks:
        return True
    exponent = rest[marks[0] + 1 :]
    return _digits(exponent[1:] if exponent[:1] in ("-", "+") else exponent)


def test_the_steps_transcribed_are_in_the_fetched_text(html_rules: str) -> None:
    for step in (
        "Skip ASCII whitespace within input given position",
        f"Change value and divisor to {MINUS}1",
        'Advance position to the next character. (The " + " is ignored, but it is not conforming.)',
        "and the character after the character indicated by position is an ASCII digit , then"
        " set value to zero and jump to the step labeled fraction",
        "Multiply value by ten raised to the exponent th power",
        "Let S be the set of finite IEEE 754 double-precision floating-point values"
        f" except {MINUS}0",
        "A series of one or more ASCII digits",
    ):
        assert step in html_rules, step


@pytest.mark.parametrize("length", [0, 1, 2, 3, 4])
def test_every_short_string_reads_as_the_steps_say(length: int) -> None:
    for chars in itertools.product(ALPHABET, repeat=length):
        text = "".join(chars)
        assert parse_number(text) == _reference(text), repr(text)
        valid = _valid_reference(text) and _reference(text) is not None
        assert is_valid_number(text) == valid, repr(text)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_seeded_longer_strings_read_as_the_steps_say(seed: int) -> None:
    rng = random.Random(seed)
    pieces = [*ALPHABET, "123", "000", "e30", "e-30", "e308", "e-330", ".5", "9" * 20]
    for _ in range(20_000):
        text = "".join(rng.choice(pieces) for _ in range(rng.randint(1, 8)))
        assert parse_number(text) == _reference(text), repr(text)


def test_a_duration_is_read_with_these_rules_and_strict_asks_for_a_valid_number() -> None:
    for text in ("12ms", "+5", ".5", "1.", "1e", "-0", "1e400", "x"):
        (metric,) = parse(f"a;dur={text}")
        assert metric.dur == _reference(text)
        if is_valid_number(text):
            assert parse(f"a;dur={text}", strict=True) == [Metric("a", _reference(text))]
        else:
            with pytest.raises(ServerTimingError, match="valid floating-point number"):
                parse(f"a;dur={text}", strict=True)

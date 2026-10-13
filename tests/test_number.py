"""Durations follow HTML 2.3.4.3. Cases are written by hand from the algorithm steps at
https://html.spec.whatwg.org/multipage/common-microsyntaxes.html#rules-for-parsing-floating-point-number-values
"""

from __future__ import annotations

import math

import pytest

from servertiming._number import format_number, is_valid_number, parse_number

READ = [
    ("123.4", 123.4),
    ("0", 0.0),
    ("-0", 0.0),
    ("-0.0", 0.0),
    ("-1e-400", 0.0),
    ("  \t\n\f\r7", 7.0),
    ("+5", 5.0),
    ("-.5", -0.5),
    (".5", 0.5),
    ("1.", 1.0),
    ("1.e2", 100.0),
    ("1e", 1.0),
    ("1e+", 1.0),
    ("1e-", 1.0),
    ("1ex", 1.0),
    ("2E3", 2000.0),
    ("1.5e-1", 0.15),
    ("12ms", 12.0),
    ("1.5.2", 1.5),
    ("1_000", 1.0),
    ("0.1", 0.1),
    ("9007199254740993", 9007199254740992.0),
    ("1.7976931348623157e308", 1.7976931348623157e308),
    ("1e" + "0" * 5000 + "1", 10.0),
]


@pytest.mark.parametrize(("text", "value"), READ)
def test_parse_number_follows_the_html_rules(text: str, value: float) -> None:
    result = parse_number(text)
    assert result == value
    assert result is not None
    assert math.copysign(1.0, result) == math.copysign(1.0, value)


@pytest.mark.parametrize(
    "text",
    [
        "",
        " ",
        "-",
        "+",
        ".",
        ".e5",
        "-.",
        "+-1",
        "--1",
        "e5",
        "abc",
        "\v1",
        "inf",
        "nan",
        "1e999",
        "-1e999",
        "1.8e308",
    ],
)
def test_parse_number_errors(text: str) -> None:
    assert parse_number(text) is None


@pytest.mark.parametrize("text", ["0", "-1", "1.5", ".5", "-.5", "1e5", "1E-5", "1.5e+3"])
def test_valid_numbers(text: str) -> None:
    assert is_valid_number(text)


@pytest.mark.parametrize("text", ["", "+1", "1.", "1e", " 1", "1 ", "1.5.2", "inf", "1e999"])
def test_invalid_numbers(text: str) -> None:
    assert not is_valid_number(text)


@pytest.mark.parametrize("value", [0.1, 123.4, 1e-7, 5e-324, 1.7976931348623157e308, 2.0**60])
def test_format_number_round_trips(value: float) -> None:
    text = format_number(value)
    assert is_valid_number(text)
    assert parse_number(text) == value

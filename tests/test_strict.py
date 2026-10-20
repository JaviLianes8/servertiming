"""Strict parsing against the ABNF in spec section 2 with RFC 9110 5.6 definitions.

Cases are written by hand from the grammar."""

from __future__ import annotations

import pickle

import pytest

from timingheader import Metric, ServerTimingError, parse

VALID = [
    ("", []),
    ("miss, db;dur=53, app;dur=47.2", [Metric("miss"), Metric("db", 53.0), Metric("app", 47.2)]),
    ('cache;desc="Cache Read";dur=23.2', [Metric("cache", 23.2, "Cache Read")]),
    ("db ; dur = 1 ;\tdesc = x", [Metric("db", 1.0, "x")]),
    ("  db  ", [Metric("db")]),
    ("a , b,\tc", [Metric("a"), Metric("b"), Metric("c")]),
    ('db;dur="1.5"', [Metric("db", 1.5)]),
    ("db;dur=-1.5e+3", [Metric("db", -1500.0)]),
    ("db;dur=.5", [Metric("db", 0.5)]),
    ('db;desc="q\\"\\\\ \xe9"', [Metric("db", desc='q"\\ \xe9')]),
    ("db;hit=1;Region=eu", [Metric("db", params=(("hit", "1"), ("region", "eu")))]),
]


@pytest.mark.parametrize(("value", "expected"), VALID)
def test_strict_accepts_the_grammar(value: str, expected: list[Metric]) -> None:
    assert parse(value, strict=True) == expected


@pytest.mark.parametrize(("value", "expected"), VALID)
def test_strict_and_lenient_agree_on_valid_input(value: str, expected: list[Metric]) -> None:
    assert parse(value) == expected


INVALID = [
    ("[x]", 0, "expected a metric name"),
    ("db;", 3, "expected a parameter name"),
    ("db;dur", 6, "expected '='"),
    ("db;dur=", 7, "expected a token or quoted string"),
    ("db;desc=d1 d2", 11, "expected ',' or ';'"),
    ('db;desc="a" b', 12, "expected ',' or ';'"),
    ("db==", 2, "expected ',' or ';'"),
    ('db;desc="open', 8, "unterminated quoted string"),
    ('db;desc="a\\', 8, "unterminated quoted string"),
    ('db;desc="a\nb"', 10, "not allowed in a quoted string"),
    ('db;desc="a\x7f"', 10, "not allowed in a quoted string"),
    ('db;desc="\\\x00"', 10, "not allowed in a quoted string"),
    ('db;desc="☃"', 9, "not allowed in a quoted string"),
    ("db;dur=1;DUR=2", 9, "'dur' is repeated"),
    ("db;x=1;x=2", 7, "'x' is repeated"),
    ("db;dur=fast", 7, "dur is not a valid floating-point number"),
    ("db;dur=1.", 7, "dur is not a valid floating-point number"),
    ("db;dur=+1", 7, "dur is not a valid floating-point number"),
    ("db;dur=1e999", 7, "dur is not a valid floating-point number"),
    ("db\r\n", 2, "expected ',' or ';'"),
    # RFC 9110 5.6.1.1: a sender must not generate empty list elements.
    (",", 0, "empty list element"),
    ("a,,b", 2, "empty list element"),
    ("a , ,b", 4, "empty list element"),
    ("a, ", 3, "empty list element"),
    (" ,a", 1, "empty list element"),
]


@pytest.mark.parametrize(("value", "position", "message"), INVALID)
def test_strict_rejects_with_the_position(value: str, position: int, message: str) -> None:
    with pytest.raises(ServerTimingError, match=message) as caught:
        parse(value, strict=True)
    assert caught.value.position == position
    assert caught.value.field == 0


def test_strict_reports_which_field_failed() -> None:
    with pytest.raises(ServerTimingError) as caught:
        parse(["db;dur=1", "ok", "x;"], strict=True)
    assert (caught.value.field, caught.value.position) == (2, 2)


def test_strict_reads_each_field_on_its_own() -> None:
    assert parse(["a;desc=x", "b"], strict=True) == [Metric("a", desc="x"), Metric("b")]
    with pytest.raises(ServerTimingError):
        parse(['a;desc="x', 'y"'], strict=True)


def test_the_error_message_names_what_was_found() -> None:
    with pytest.raises(ServerTimingError, match=r"at position 2 \(found '='\)"):
        parse("db=", strict=True)
    with pytest.raises(ServerTimingError, match=r"found the end"):
        parse("db;", strict=True)


def test_the_error_survives_pickling() -> None:
    with pytest.raises(ServerTimingError) as caught:
        parse("db;", strict=True)
    copy = pickle.loads(pickle.dumps(caught.value))
    assert (copy.message, copy.position, copy.field) == (
        caught.value.message,
        caught.value.position,
        caught.value.field,
    )
    assert str(copy) == str(caught.value)

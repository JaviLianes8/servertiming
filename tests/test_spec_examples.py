"""The example in section 6 of https://w3c.github.io/server-timing/ (fetched 2026-10-13):
three Server-Timing header lines and one trailer, and the six metrics they carry."""

from __future__ import annotations

from timingheader import Metric, parse

HEADERS = [
    "miss, db;dur=53, app;dur=47.2",
    "customView, dc;desc=atl",
    'cache;desc="Cache Read";dur=23.2',
]
TRAILER = "total;dur=123.4"
EXPECTED = [
    Metric("miss"),
    Metric("db", dur=53.0),
    Metric("app", dur=47.2),
    Metric("customView"),
    Metric("dc", desc="atl"),
    Metric("cache", dur=23.2, desc="Cache Read"),
    Metric("total", dur=123.4),
]


def test_headers_and_trailer_read_together() -> None:
    assert parse([*HEADERS, TRAILER]) == EXPECTED


def test_the_example_is_valid_in_strict_mode() -> None:
    assert parse([*HEADERS, TRAILER], strict=True) == EXPECTED


def test_browser_view_of_the_example() -> None:
    view = [(m.name, m.duration, m.description) for m in parse([*HEADERS, TRAILER])]
    assert view[0] == ("miss", 0.0, "")
    assert view[4] == ("dc", 0.0, "atl")


def test_the_abnf_token_characters_make_a_valid_name() -> None:
    # Every tchar from RFC 9110 5.6.2, https://www.rfc-editor.org/rfc/rfc9110.txt
    name = "!#$%&'*+-.^_`|~09azAZ"
    assert parse(name, strict=True) == [Metric(name)]

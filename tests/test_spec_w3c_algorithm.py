"""The step-by-step algorithm of the W3C Editor's Draft, and where `parse` departs from it.

Source: "parse a server-timing header field" in the Bikeshed source of the Editor's Draft,
and "get, decode, and split" plus "collect an HTTP quoted string" in the WHATWG Fetch
Standard (URLs, commits and sha256 in tests/upstream/MANIFEST.json, fetched 2026-10-20).
The transcription below was written by hand from those steps; the tests check that the
steps it follows are still the ones in the fetched text. `parse` follows the
web-platform-tests corpus where the two conflict, and the GUIDE lists the differences.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import prose, upstream_document
from test_wpt import CASES, _case

from timingheader import parse
from timingheader._number import parse_number

_ASCII_WHITESPACE = "\t\n\f\r "


def _collect(text: str, position: int, stop: str) -> tuple[str, int]:
    end = position
    while end < len(text) and text[end] not in stop:
        end += 1
    return text[position:end], end


def _quoted(text: str, position: int, extract: bool) -> tuple[str, int]:
    start, value = position, ""
    position += 1
    while True:
        part, position = _collect(text, position, '"\\')
        value += part
        if position >= len(text):
            break
        char = text[position]
        position += 1
        if char == "\\":
            if position >= len(text):
                value += "\\"
                break
            value += text[position]
            position += 1
        else:
            break
    return (value if extract else text[start:position]), position


def _split(value: str) -> list[str]:
    values, position, temporary = [], 0, ""
    while True:
        part, position = _collect(value, position, '",')
        temporary += part
        if position < len(value) and value[position] == '"':
            part, position = _quoted(value, position, extract=False)
            temporary += part
            if position < len(value):
                continue
        values.append(temporary.strip(" \t"))
        temporary = ""
        if position >= len(value):
            return values
        position += 1


def _field(field: str) -> tuple[str, float, str] | None:
    name, position = _collect(field, 0, ";")
    name = name.strip(_ASCII_WHITESPACE)
    if not name:
        return None
    params: dict[str, str] = {}
    while position < len(field):
        position += 1
        key, position = _collect(field, position, "=")
        key = key.strip(_ASCII_WHITESPACE)
        if not key or key in params:
            continue
        position += 1
        while position < len(field) and field[position] in _ASCII_WHITESPACE:
            position += 1
        if position < len(field) and field[position] == '"':
            value, position = _quoted(field, position, extract=True)
            _, position = _collect(field, position, ";")
        else:
            raw, position = _collect(field, position, ";")
            value = raw.strip(_ASCII_WHITESPACE)
        params[key] = value
    dur = parse_number(params["dur"]) if "dur" in params else None
    return name, 0.0 if dur is None else dur, params.get("desc", "")


def editors_draft(fields: list[str]) -> list[tuple[str, float, str]]:
    """What the Editor's Draft algorithm exposes for the field values of one response."""
    found = (_field(value) for value in _split(", ".join(fields)))
    return [metric for metric in found if metric is not None]


def _ours(fields: list[str]) -> list[tuple[str, float, str]]:
    return [(m.name, m.duration, m.description) for m in parse(fields)]


def test_the_transcribed_steps_are_the_ones_in_the_fetched_texts() -> None:
    spec = prose(upstream_document("server-timing.bs"))
    steps = spec.split("To parse a server-timing header field given a string |field|:", 1)[1]
    steps = steps.split("Return |metric|", 1)[0]
    for step in [
        "Let name be the result of [=collecting a sequence of code points=] from |field| that "
        "are not equal to U+003B (;)",
        "If name is an empty string, return null.",
        "that are not equal to U+003D (=), given |position|",
        "If |paramName| is an empty string or |params|[|paramName|] [=map/exists=]",
        "with the extract-value flag set",
        "Let |paramValue| be the result of [=strip leading and trailing ASCII "
        "whitespace|stripping=]",
    ]:
        assert step in steps, step
    fetch = prose(upstream_document("whatwg-fetch.html"))
    assert "get, decode, and split" in fetch


@pytest.mark.parametrize(
    ("value", "draft", "ours"),
    [
        ("a=1, b", [("a=1", 0.0, ""), ("b", 0.0, "")], [("a", 0.0, ""), ("b", 0.0, "")]),
        ("[x], b", [("[x]", 0.0, ""), ("b", 0.0, "")], [("b", 0.0, "")]),
        ("a;Dur=5", [("a", 0.0, "")], [("a", 5.0, "")]),
        ("cache;desc=d1 d2", [("cache", 0.0, "d1 d2")], [("cache", 0.0, "d1")]),
        ("a;;dur=1", [("a", 0.0, "")], [("a", 1.0, "")]),
    ],
)
def test_the_differences_the_guide_lists(
    value: str, draft: list[tuple[str, float, str]], ours: list[tuple[str, float, str]]
) -> None:
    upstream_document("server-timing.bs")
    assert editors_draft([value]) == draft
    assert _ours([value]) == ours
    guide = (Path(__file__).resolve().parents[1] / "GUIDE.md").read_text(encoding="utf-8")
    assert f"`{value}`" in guide


def test_the_algorithm_and_the_corpus_disagree_on_35_of_85_cases() -> None:
    upstream_document("server-timing.bs")
    disagree = []
    for number in CASES:
        fields, expected = _case(number)
        want = [(e["name"], e.get("dur", 0), e.get("desc", "")) for e in expected]
        assert _ours(fields) == want
        if editors_draft(fields) != want:
            disagree.append(number)
    assert len(disagree) == 35, disagree

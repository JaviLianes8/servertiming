"""Seeded property tests: hostile text never crashes either parser, and strict mode accepts
exactly the grammar.

``GRAMMAR`` below is a regular expression written by hand from the W3C Server Timing
ABNF and the RFC 9110 token, quoted-string and OWS rules (the same rules the spec tests
read from the fetched text); it shares no code with the library.
"""

from __future__ import annotations

import math
import random
import re

import pytest
from generators import WIRE, hostile, near_valid

from timingheader import Metric, ServerTimingError, build, parse
from timingheader._cli import fields_from_lines
from timingheader._number import is_valid_number

_TCHAR = r"[!#$%&'*+\-.^_`|~0-9A-Za-z]"
_QS = r'"(?:[\t \x21\x23-\x5b\x5d-\x7e\x80-\xff]|\\[\t \x20-\x7e\x80-\xff])*"'
_PARAM = rf"{_TCHAR}+[ \t]*=[ \t]*(?:{_TCHAR}+|{_QS})"
_METRIC = rf"{_TCHAR}+(?:[ \t]*;[ \t]*{_PARAM})*"
GRAMMAR = re.compile(rf"[ \t]*(?:{_METRIC}(?:[ \t]*,[ \t]*{_METRIC})*)?[ \t]*")
_PAIR = re.compile(rf";[ \t]*({_TCHAR}+)[ \t]*=[ \t]*({_TCHAR}+|{_QS})")
SEEDS = [11, 2026, 99991]
# Everything a str can hold that matters: controls, ASCII, obs-text, beyond, a surrogate.
ANY = [chr(c) for c in (*range(0x100), 0x100, 0x2603, 0x212A, 0xD800, 0x1F600)]


def _grammar_accepts(text: str) -> bool:
    if GRAMMAR.fullmatch(text) is None:
        return False
    # Inside a quoted string a ';' is text, so pairs are read with the quoted strings whole.
    for metric in re.split(rf",(?=(?:[^\"]|{_QS})*$)", text):
        keys = [(key.lower(), value) for key, value in _PAIR.findall(metric)]
        names = [key for key, _ in keys]
        if len(set(names)) != len(names):
            return False
        if any(key == "dur" and not is_valid_number(value) for key, value in keys):
            return False
    return True


def _texts(seed: int, count: int) -> list[str]:
    rng = random.Random(seed)
    return [
        near_valid(rng) if index % 2 else hostile(rng, ANY if index % 3 else WIRE)
        for index in range(count)
    ]


@pytest.mark.parametrize("seed", SEEDS)
def test_the_lenient_parser_never_raises_and_keeps_its_invariants(seed: int) -> None:
    for text in _texts(seed, 20_000):
        for metric in parse(text):
            assert metric.name and re.fullmatch(f"{_TCHAR}+", metric.name), text
            assert metric.dur is None or math.isfinite(metric.dur), text
            assert metric.dur is None or str(metric.dur) != "-0.0", text
            keys = [key for key, _ in metric.params]
            assert len(set(keys)) == len(keys) and not {"dur", "desc"} & set(keys), text
            assert all(key == key.lower() for key in keys), text


@pytest.mark.parametrize("seed", SEEDS)
def test_strict_mode_accepts_exactly_the_grammar(seed: int) -> None:
    accepted = 0
    for text in _texts(seed, 20_000):
        try:
            got = parse(text, strict=True)
        except ServerTimingError as error:
            assert not _grammar_accepts(text), text
            assert error.field == 0 and 0 <= (error.position or 0) <= len(text), text
            assert len(str(error)) < 300, text
            continue
        assert _grammar_accepts(text), text
        assert got == parse(text), text
        accepted += 1
    assert accepted > 500


@pytest.mark.parametrize("seed", SEEDS)
def test_what_strict_mode_accepts_builds_back_to_the_same_metrics(seed: int) -> None:
    for text in _texts(seed, 10_000):
        try:
            metrics = parse(text, strict=True)
        except ServerTimingError:
            continue
        rebuilt = build(metrics)
        assert parse(rebuilt, strict=True) == metrics, text
        assert build(parse(rebuilt)) == rebuilt, text


@pytest.mark.parametrize("seed", SEEDS)
def test_build_refuses_or_writes_a_value_strict_mode_reads_back(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(4000):

        def text() -> str:
            return "".join(rng.choice(ANY) for _ in range(rng.randint(0, 6)))

        metric = Metric(text(), rng.choice([None, rng.uniform(-1e9, 1e9)]), text())
        try:
            header = build([metric])
        except ServerTimingError as error:
            assert error.position is None and len(str(error)) < 300
            continue
        assert parse(header, strict=True) == [metric]


@pytest.mark.parametrize("seed", SEEDS)
def test_the_command_reads_any_lines_without_raising(seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(2000):
        lines = [hostile(rng, ANY, 12) for _ in range(rng.randint(0, 6))]
        if rng.random() < 0.5:
            lines.insert(0, "HTTP/1.1 200 OK")
            lines.insert(rng.randint(1, len(lines)), "Server-Timing: " + near_valid(rng))
        for field in fields_from_lines(lines):
            assert field == field.strip(" \t") and field
            parse(field)

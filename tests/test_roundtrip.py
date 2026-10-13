"""Seeded round trip: whatever ``build`` writes, both parsers read back unchanged."""

from __future__ import annotations

import random

from servertiming import Metric, build, parse
from servertiming._syntax import TCHARS

_TOKEN = sorted(TCHARS)
# Everything a quoted string can carry, weighted towards the characters that need care.
_TEXT = [chr(c) for c in (9, *range(32, 127), *range(128, 256))] + ['"', "\\", ",", ";", "="] * 8


def _token(rng: random.Random) -> str:
    return "".join(rng.choice(_TOKEN) for _ in range(rng.randint(1, 8)))


def _text(rng: random.Random) -> str:
    return "".join(rng.choice(_TEXT) for _ in range(rng.randint(0, 12)))


def _dur(rng: random.Random) -> float | None:
    kind = rng.randrange(5)
    if kind == 0:
        return None
    if kind == 1:
        return float(rng.randint(0, 10_000))
    if kind == 2:
        return rng.uniform(-1e6, 1e6)
    if kind == 3:
        return rng.uniform(0, 1) * 10.0 ** rng.randint(-320, 300)
    return rng.random()


def _metric(rng: random.Random) -> Metric:
    params: dict[str, str] = {}
    for _ in range(rng.randrange(3)):
        key = _token(rng).lower()
        if key not in ("dur", "desc"):
            params.setdefault(key, _text(rng))
    desc = _text(rng) if rng.random() < 0.7 else None
    return Metric(_token(rng), _dur(rng), desc, tuple(params.items()))


def test_build_then_parse_is_the_identity() -> None:
    rng = random.Random(20261013)
    for _ in range(2000):
        metrics = [_metric(rng) for _ in range(rng.randint(1, 4))]
        header = build(metrics)
        assert parse(header) == metrics, header
        assert parse(header, strict=True) == metrics, header


def test_every_built_header_stays_on_one_line() -> None:
    rng = random.Random(7)
    for _ in range(500):
        header = build([_metric(rng)])
        assert not any(char in header for char in "\r\n\x00")
        assert all(ord(char) < 256 for char in header)

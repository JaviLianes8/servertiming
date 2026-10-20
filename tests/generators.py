"""Seeded generators of Server-Timing text, shared by the fuzz, hostile and oracle tests.

Every generator takes a ``random.Random`` so a failure is reproduced by its seed.
"""

from __future__ import annotations

import random

from timingheader._syntax import TCHARS

TOKEN = sorted(TCHARS)
# Characters a header field value can carry on the wire: HTAB, SP, VCHAR and obs-text.
WIRE = [chr(c) for c in (9, *range(32, 127), *range(128, 256))]
# The characters that steer the parsers, repeated so they turn up often.
SIGNIFICANT = [";", ",", "=", '"', "\\", " ", "\t", ".", "-", "+", "e", "E", "0", "1", "9"]
WORDS = ["dur", "desc", "DUR", "Desc", "dur=", "desc=", ";dur=", ";desc=", "1e3", "-0", ".5"]
NUMBERS = [
    "0",
    "-0",
    "1",
    "+1",
    "-1",
    ".5",
    "-.5",
    "1.",
    "1.e2",
    "1e",
    "1e+",
    "1e-",
    "1ex",
    "12ms",
    "1.5.2",
    "1_000",
    "1e309",
    "-1e309",
    "1e-400",
    "2.5e-3",
    "007",
    "9007199254740993",
    "1.7976931348623157e308",
    "1.7976931348623159e308",
    "inf",
    "NaN",
    "0x10",
    " 5",
    "5 ",
    "\t5",
    "",
    ".",
    "-",
    "+",
    "e5",
    ".e1",
    "1e+5",
    "1E-5",
    "123456789.987654321",
]


def hostile(rng: random.Random, alphabet: list[str], size: int = 40) -> str:
    """Random text over ``alphabet`` mixed with the significant characters and words."""
    parts: list[str] = []
    for _ in range(rng.randint(0, size)):
        roll = rng.random()
        if roll < 0.45:
            parts.append(rng.choice(SIGNIFICANT))
        elif roll < 0.6:
            parts.append(rng.choice(WORDS))
        elif roll < 0.75:
            parts.append("".join(rng.choice(TOKEN) for _ in range(rng.randint(1, 4))))
        else:
            parts.append(rng.choice(alphabet))
    return "".join(parts)


def _value(rng: random.Random) -> str:
    roll = rng.random()
    if roll < 0.3:
        return rng.choice(NUMBERS)
    if roll < 0.55:
        return "".join(rng.choice(TOKEN) for _ in range(rng.randint(0, 6)))
    body = "".join(rng.choice([*WIRE, '\\"', "\\\\", ",", ";"]) for _ in range(rng.randint(0, 8)))
    return f'"{body}"' if rng.random() < 0.9 else f'"{body}'


def _ows(rng: random.Random) -> str:
    return rng.choice(["", "", "", " ", "\t", "  "])


def near_valid(rng: random.Random) -> str:
    """A field value built from the grammar, with an occasional slip a parser must survive."""
    metrics: list[str] = []
    for _ in range(rng.randint(0, 4)):
        name = "".join(rng.choice(TOKEN) for _ in range(rng.randint(1, 6)))
        parts = [name if rng.random() > 0.05 else rng.choice(['"q"', "[x]", ""])]
        for _ in range(rng.randint(0, 4)):
            key = rng.choice(["dur", "desc", "DUR", "Desc", "x", "hit", ""])
            junk = rng.choice(["", "", "", "", " junk", '"q"', "=", " a b"])
            parts.append(f"{_ows(rng)};{_ows(rng)}{key}{_ows(rng)}={_ows(rng)}{_value(rng)}{junk}")
        metrics.append("".join(parts))
    return rng.choice([",", ", ", " ,", ",,", ", ,"]).join(metrics)


def wire_fields(rng: random.Random) -> list[str]:
    """One to three field values that can be sent as response headers, trimmed as a
    recipient sees them: only HTAB, SP, VCHAR and obs-text, no CR, LF or NUL."""
    count = rng.choice([1, 1, 1, 2, 3])
    fields = []
    for _ in range(count):
        text = near_valid(rng) if rng.random() < 0.6 else hostile(rng, WIRE)
        fields.append(text.strip(" \t"))
    return fields


VALID_NUMBERS = ["0", "-0", "1", "53", "47.2", ".5", "-.5", "0.000001", "1e3", "2.5E-3", "-7e+2"]
SPECIAL = '"' + chr(92)  # a quote and a backslash, which need an escape
QDTEXT = [c for c in WIRE if c not in SPECIAL]


def _valid_value(rng: random.Random, key: str) -> str:
    if key.lower() == "dur":
        number = rng.choice(VALID_NUMBERS)
        return f'"{number}"' if rng.random() < 0.2 else number
    if rng.random() < 0.4:
        return "".join(rng.choice(TOKEN) for _ in range(rng.randint(1, 6)))
    body = []
    for _ in range(rng.randint(0, 8)):
        char = rng.choice([*QDTEXT, '"', "\\", ",", ";", "="])
        body.append("\\" + char if char in SPECIAL or rng.random() < 0.05 else char)
    return '"' + "".join(body) + '"'


def valid_field(rng: random.Random) -> str:
    """A field value that follows the grammar exactly with the sender rules."""
    metrics = []
    for _ in range(rng.randint(1, 4)):
        parts = ["".join(rng.choice(TOKEN) for _ in range(rng.randint(1, 6)))]
        keys = rng.sample(["dur", "desc", "DUR", "x", "hit", "Pop"], rng.randint(0, 3))
        if len({key.lower() for key in keys}) != len(keys):
            keys = keys[:1]
        for key in keys:
            value = _valid_value(rng, key)
            parts.append(f"{_ows(rng)};{_ows(rng)}{key}{_ows(rng)}={_ows(rng)}{value}")
        metrics.append("".join(parts))
    return f"{_ows(rng)},{_ows(rng)}".join(metrics)

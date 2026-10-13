"""Command line: show the metrics in Server-Timing values and check them against the grammar."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import TextIO

from ._errors import ServerTimingError
from ._metric import Metric
from ._number import format_number
from ._parse import parse_lenient
from ._strict import parse_strict

_PREFIX = "server-timing:"


def main(argv: Sequence[str] | None = None, stdin: TextIO | None = None) -> int:
    """Run the command; returns 0 when every value is valid, 1 when not, 2 for no input."""
    parser = argparse.ArgumentParser(
        prog="servertiming",
        description="Show the metrics in Server-Timing values and check them against the "
        "grammar. With no VALUE, lines are read from stdin; given response headers (as "
        "from curl -sI), only the Server-Timing lines are used.",
    )
    parser.add_argument("values", nargs="*", metavar="VALUE", help="a Server-Timing value")
    parser.add_argument("--json", action="store_true", help="print the metrics as JSON")
    args = parser.parse_args(argv)
    fields = _fields(args.values or (stdin or sys.stdin).read().splitlines())
    if not fields:
        print("no Server-Timing value given", file=sys.stderr)
        return 2
    metrics = parse_lenient(fields)
    print(_as_json(metrics) if args.json else _as_table(metrics))
    errors = _errors(fields)
    for error in errors:
        print(f"invalid value {(error.field or 0) + 1}: {error.message}", file=sys.stderr)
    return 1 if errors else 0


def _fields(lines: Sequence[str]) -> list[str]:
    tagged = [line for line in lines if line.lower().startswith(_PREFIX)]
    chosen = [line[len(_PREFIX) :] for line in tagged] if tagged else list(lines)
    return [line.strip(" \t\r\n") for line in chosen if line.strip(" \t\r\n")]


def _errors(fields: list[str]) -> list[ServerTimingError]:
    found: list[ServerTimingError] = []
    for index, field in enumerate(fields):
        try:
            parse_strict(field, index)
        except ServerTimingError as error:
            found.append(error)
    return found


def _as_json(metrics: list[Metric]) -> str:
    rows = [
        {"name": m.name, "dur": m.dur, "desc": m.desc, "params": dict(m.params)} for m in metrics
    ]
    return json.dumps(rows, indent=2, ensure_ascii=False)


def _as_table(metrics: list[Metric]) -> str:
    rows = [("name", "dur", "desc")]
    for m in metrics:
        extra = "".join(f" {key}={value!r}" for key, value in m.params)
        dur = "" if m.dur is None else format_number(m.dur)
        rows.append((m.name, dur, ("" if m.desc is None else repr(m.desc)) + extra))
    widths = [max(len(row[i]) for row in rows) for i in range(2)]
    return "\n".join(f"{a:<{widths[0]}}  {b:>{widths[1]}}  {c}".rstrip() for a, b, c in rows)

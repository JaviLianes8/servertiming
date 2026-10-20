"""Command line: show the metrics in Server-Timing values and check them against the grammar."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from typing import TextIO

from ._errors import ServerTimingError
from ._metric import Metric
from ._number import format_number
from ._parse import parse_lenient
from ._strict import parse_strict

_PREFIX = "server-timing:"
_OWS = " \t"
# A status line or any "name:" line means the input is a header block, not bare values.
_HEADER_LINE = re.compile(r"HTTP/|[!#$%&'*+.^_`|~0-9A-Za-z-]+:")


def main(argv: Sequence[str] | None = None, stdin: TextIO | None = None) -> int:
    """Run the command; returns 0 when every value is valid, 1 when not, 2 for no value."""
    parser = argparse.ArgumentParser(
        prog="timingheader",
        description="Show the metrics in Server-Timing values and check them against the "
        "grammar. With no VALUE, lines are read from stdin; given response headers (as "
        "from curl -sI), only the Server-Timing fields are used.",
    )
    parser.add_argument("values", nargs="*", metavar="VALUE", help="a Server-Timing value")
    parser.add_argument("--json", action="store_true", help="print the metrics as JSON")
    args = parser.parse_args(argv)
    fields = [v for v in args.values if v.strip(_OWS)] if args.values else _read(stdin)
    if not fields:
        print("no Server-Timing value given", file=sys.stderr)
        return 2
    metrics = parse_lenient(fields)
    _write(_as_json(metrics) if args.json else _as_table(metrics))
    errors = _errors(fields)
    for error in errors:
        print(f"invalid value {(error.field or 0) + 1}: {error.message}", file=sys.stderr)
    return 1 if errors else 0


def _read(stdin: TextIO | None) -> list[str]:
    # Header bytes map one to one onto characters (ISO-8859-1), as browsers read them.
    text = sys.stdin.buffer.read().decode("latin-1") if stdin is None else stdin.read()
    # Only LF ends a line in HTTP; str.splitlines would also split on obs-text such as 0x85.
    return fields_from_lines([line.removesuffix("\r") for line in text.split("\n")])


def fields_from_lines(lines: Sequence[str]) -> list[str]:
    """Bare values one per line, or the Server-Timing fields of a header block."""
    if not any(_HEADER_LINE.match(line) for line in lines):
        return [line.strip(_OWS) for line in lines if line.strip(_OWS)]
    fields: list[str] = []
    inside = False
    for line in lines:
        if inside and line[:1] in (" ", "\t"):
            # An obsolete folded line continues the field above it (RFC 9112 5.2).
            fields[-1] = " ".join(part for part in (fields[-1], line.strip(_OWS)) if part)
            continue
        inside = line.lower().startswith(_PREFIX)
        if inside:
            fields.append(line[len(_PREFIX) :].strip(_OWS))
    return [field for field in fields if field]


def _errors(fields: list[str]) -> list[ServerTimingError]:
    found: list[ServerTimingError] = []
    for index, field in enumerate(fields):
        try:
            parse_strict(field, index)
        except ServerTimingError as error:
            found.append(error)
    return found


def _write(text: str) -> None:
    # A console or pipe that cannot show a character gets an escape, not a traceback.
    encoding = sys.stdout.encoding or "utf-8"
    sys.stdout.write(text.encode(encoding, "backslashreplace").decode(encoding) + "\n")


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

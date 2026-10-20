"""Command line: show the metrics in Server-Timing values and check them against the grammar."""

from __future__ import annotations

import argparse
import errno
import json
import os
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
        "from curl -sI), only the Server-Timing fields of the last response are used.",
    )
    parser.add_argument("values", nargs="*", metavar="VALUE", help="a Server-Timing value")
    parser.add_argument("--json", action="store_true", help="print the metrics as JSON")
    args = parser.parse_args(argv)
    if args.values:
        # Blank arguments are dropped, but a value keeps its number on the command line.
        given = [(n, v) for n, v in enumerate(args.values, 1) if v.strip(_OWS)]
    else:
        given = list(enumerate(_read(stdin), 1))
    if not given:
        print("no Server-Timing value given", file=sys.stderr)
        return 2
    fields = [value for _, value in given]
    metrics = parse_lenient(fields)
    _write(_as_json(metrics) if args.json else _as_table(metrics))
    errors = _errors(fields)
    for error in errors:
        number = given[error.field or 0][0]
        print(f"invalid value {number}: {error.message}", file=sys.stderr)
    return 1 if errors else 0


def _read(stdin: TextIO | None) -> list[str]:
    # Header bytes map one to one onto characters (ISO-8859-1), as browsers read them.
    text = sys.stdin.buffer.read().decode("latin-1") if stdin is None else stdin.read()
    # Only LF ends a line in HTTP; str.splitlines would also split on obs-text such as 0x85.
    return fields_from_lines([line.removesuffix("\r") for line in text.split("\n")])


def fields_from_lines(lines: Sequence[str]) -> list[str]:
    """Bare values one per line, or the Server-Timing fields of a header block.

    A block holding several responses (redirects followed, interim responses) gives the
    fields of the last one only, the response a browser exposes.
    """
    if not any(_HEADER_LINE.match(line) for line in lines):
        return [line.strip(_OWS) for line in lines if line.strip(_OWS)]
    # Each field is kept as its parts and joined once, so many folded lines stay linear.
    fields: list[list[str]] = []
    inside = False
    for line in lines:
        if line.startswith("HTTP/"):
            fields, inside = [], False
            continue
        if inside and line[:1] in (" ", "\t"):
            # An obsolete folded line continues the field above it (RFC 9112 5.2).
            fields[-1].append(line.strip(_OWS))
            continue
        inside = line[: len(_PREFIX)].lower() == _PREFIX
        if inside:
            fields.append([line[len(_PREFIX) :].strip(_OWS)])
    joined = (" ".join(part for part in parts if part) for parts in fields)
    return [field for field in joined if field]


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
    try:
        sys.stdout.write(text.encode(encoding, "backslashreplace").decode(encoding) + "\n")
        sys.stdout.flush()
    except OSError as error:
        # A reader that stops early (| head) is not an error in the values: stop writing
        # and let the exit status still say whether they are valid.
        if not isinstance(error, BrokenPipeError) and error.errno != errno.EINVAL:
            raise
        _discard_stdout()


def _discard_stdout() -> None:
    # Python flushes stdout again at exit; pointing it at the null device keeps that quiet.
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)
    except (OSError, ValueError):
        sys.stdout = open(os.devnull, "w")  # noqa: SIM115


def _as_json(metrics: list[Metric]) -> str:
    rows = [
        {"name": m.name, "dur": m.dur, "desc": m.desc, "params": dict(m.params)} for m in metrics
    ]
    # ASCII escapes keep the JSON valid on any stdout, whatever characters it can encode.
    return json.dumps(rows, indent=2, ensure_ascii=True)


def _as_table(metrics: list[Metric]) -> str:
    rows = [("name", "dur", "desc")]
    for m in metrics:
        extra = "".join(f" {key}={value!r}" for key, value in m.params)
        dur = "" if m.dur is None else format_number(m.dur)
        rows.append((m.name, dur, ("" if m.desc is None else repr(m.desc)) + extra))
    widths = [max(len(row[i]) for row in rows) for i in range(2)]
    return "\n".join(f"{a:<{widths[0]}}  {b:>{widths[1]}}  {c}".rstrip() for a, b, c in rows)

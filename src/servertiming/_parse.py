"""Parse a Server-Timing header value into metrics, tolerating malformed input."""

from __future__ import annotations

import math

from ._metric import Metric


def parse(header: str) -> list[Metric]:
    """Read a header value into a list of metrics, skipping entries with no name.

    Unknown parameters are ignored and an unreadable duration becomes ``None`` rather
    than raising, so a partly broken header still yields the metrics it can.
    """
    metrics: list[Metric] = []
    for raw in _split(header, ","):
        entry = raw.strip()
        if not entry:
            continue
        parts = _split(entry, ";")
        name = parts[0].strip()
        if not name:
            continue
        dur: float | None = None
        desc: str | None = None
        for param in parts[1:]:
            key, _, value = param.partition("=")
            key = key.strip().lower()
            value = value.strip()
            if key == "dur":
                dur = _to_float(value)
            elif key == "desc":
                desc = _unquote(value)
        metrics.append(Metric(name=name, dur=dur, desc=desc))
    return metrics


def _split(text: str, separator: str) -> list[str]:
    parts: list[str] = []
    buffer: list[str] = []
    in_quotes = False
    escaped = False
    for char in text:
        if escaped:
            buffer.append(char)
            escaped = False
        elif char == "\\" and in_quotes:
            buffer.append(char)
            escaped = True
        elif char == '"':
            in_quotes = not in_quotes
            buffer.append(char)
        elif char == separator and not in_quotes:
            parts.append("".join(buffer))
            buffer = []
        else:
            buffer.append(char)
    parts.append("".join(buffer))
    return parts


def _to_float(value: str) -> float | None:
    try:
        number = float(value)
    except ValueError:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _unquote(value: str) -> str | None:
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return _unescape(value[1:-1])
    return value or None


def _unescape(text: str) -> str:
    result: list[str] = []
    escaped = False
    for char in text:
        if escaped:
            result.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        else:
            result.append(char)
    return "".join(result)

"""Render metrics into a Server-Timing header value."""

from __future__ import annotations

import math
from collections.abc import Iterable

from ._metric import Metric

# Characters allowed in an RFC 7230 token, the unquoted form of a name or description.
_TOKEN_CHARS = frozenset(
    "!#$%&'*+-.^_`|~0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
)


def build(metrics: Iterable[Metric]) -> str:
    """Join metrics into a single header value such as ``cpu;dur=12.3;desc="work"``."""
    return ", ".join(_render(metric) for metric in metrics)


def _render(metric: Metric) -> str:
    if not _is_token(metric.name):
        raise ValueError(f"metric name is not a valid token: {metric.name!r}")
    parts = [metric.name]
    if metric.dur is not None:
        parts.append(f"dur={_format_number(metric.dur)}")
    if metric.desc is not None:
        parts.append(f"desc={_format_desc(metric.desc)}")
    return ";".join(parts)


def _format_number(value: float) -> str:
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError(f"duration must be a finite number: {value!r}")
    text = repr(number)
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _format_desc(desc: str) -> str:
    if desc and _is_token(desc):
        return desc
    escaped = desc.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _is_token(text: str) -> bool:
    return bool(text) and all(char in _TOKEN_CHARS for char in text)

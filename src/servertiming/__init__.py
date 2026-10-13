"""Build and parse the HTTP Server-Timing header, with timing helpers for recording metrics."""

from __future__ import annotations

from collections.abc import Iterable

from ._build import build
from ._collector import Measure, Timer, Timing
from ._errors import ServerTimingError
from ._metric import Metric
from ._parse import field_list, parse_lenient
from ._strict import parse_strict

__version__ = "0.2.0"

__all__ = ["Measure", "Metric", "ServerTimingError", "Timer", "Timing", "build", "parse"]


def parse(header: str | Iterable[str], *, strict: bool = False) -> list[Metric]:
    """Read one Server-Timing field value, or several (headers then trailers), into metrics.

    By default this reads like a browser and never raises on malformed text: it keeps every
    metric it can and skips what the W3C spec says to ignore, matching the
    web-platform-tests corpus. With ``strict=True`` each field value must follow the
    grammar exactly, and the first error raises ``ServerTimingError`` with its position.
    """
    fields = field_list(header)
    if not strict:
        return parse_lenient(fields)
    metrics: list[Metric] = []
    for index, field in enumerate(fields):
        metrics.extend(parse_strict(field, index))
    return metrics

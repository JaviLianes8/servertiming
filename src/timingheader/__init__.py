"""Build and parse the HTTP Server-Timing header, with timing helpers for recording metrics."""

from __future__ import annotations

from collections.abc import Iterable

from ._build import build
from ._collector import Timing
from ._errors import ServerTimingError
from ._measure import Measure, Timer
from ._metric import Metric
from ._parse import field_list, parse_lenient
from ._strict import parse_strict

__version__ = "1.0.0"

__all__ = ["Measure", "Metric", "ServerTimingError", "Timer", "Timing", "build", "parse"]

# The public classes report the package as their home, so reprs, pickles and docs never
# name a private module that is free to change.
for _cls in (Measure, Metric, ServerTimingError, Timer, Timing):
    _cls.__module__ = __name__
    for _member in vars(_cls).values():
        if callable(_member) and str(getattr(_member, "__module__", "")).startswith(
            __name__ + "._"
        ):
            _member.__module__ = __name__
del _cls, _member


def parse(header: str | Iterable[str], *, strict: bool = False) -> list[Metric]:
    """Read one Server-Timing field value, or several (headers then trailers), into metrics.

    By default this reads like a browser and never raises on malformed text: it keeps every
    metric it can and skips what the W3C spec says to ignore, matching the
    web-platform-tests corpus. With ``strict=True`` each field value must follow the
    grammar exactly, and the first error raises ``ServerTimingError`` with its field index
    and position. A value that is not a ``str`` (or an iterable of ``str``) raises
    ``TypeError``; decode header bytes as ISO-8859-1 first.

    >>> from timingheader import parse
    >>> [(m.name, m.dur, m.desc) for m in parse('db;dur=53;desc="primary", cache;desc=d1 d2')]
    [('db', 53.0, 'primary'), ('cache', None, 'd1')]
    >>> [m.name for m in parse(["miss, db;dur=53", "total;dur=123.4"])]
    ['miss', 'db', 'total']
    >>> parse("db;dur=1, [x], a;DUR=2;dur=3", strict=False)[1].dur
    2.0
    """
    fields = field_list(header)
    if not strict:
        return parse_lenient(fields)
    metrics: list[Metric] = []
    for index, field in enumerate(fields):
        metrics.extend(parse_strict(field, index))
    return metrics

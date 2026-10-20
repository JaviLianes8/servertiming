"""Build and parse the HTTP Server-Timing header, with timing helpers for recording metrics."""

from __future__ import annotations

import functools as _functools
from typing import TYPE_CHECKING as _TYPE_CHECKING

from ._build import build
from ._collector import Timing
from ._errors import ServerTimingError
from ._measure import Measure, Timer
from ._metric import Metric
from ._strict import parse_values as _parse_values

if _TYPE_CHECKING:
    from collections.abc import Iterable

__version__ = "1.0.0"

__all__ = ["Measure", "Metric", "ServerTimingError", "Timer", "Timing", "build", "parse"]


def _relabel(obj: object) -> None:
    if str(getattr(obj, "__module__", "")).startswith(__name__ + "."):
        obj.__module__ = __name__


# Every public name reports the package as its home, so reprs, pickles and docs never name
# a private module that is free to change.
_relabel(build)
for _cls in (Measure, Metric, ServerTimingError, Timer, Timing):
    _relabel(_cls)
    for _member in vars(_cls).values():
        if isinstance(_member, property):
            for _accessor in (_member.fget, _member.fset, _member.fdel):
                _relabel(_accessor)
        elif callable(_member):
            _relabel(_member)
# The name bound by the __future__ import is not part of the API either.
del _cls, _member, _accessor, annotations


def parse(header: str | Iterable[str], *, strict: bool = False) -> list[Metric]:
    """Read one Server-Timing field value, or several (headers then trailers), into metrics.

    By default this reads like a browser and never raises on malformed text: it keeps every
    metric it can and skips what the web-platform-tests corpus skips. Where the
    step-by-step algorithm of the W3C Editor's Draft reads a malformed value differently,
    the corpus wins (the GUIDE lists the differences). With ``strict=True`` each field
    value must follow the grammar exactly, and the first error raises
    ``ServerTimingError`` with its field index and position. A value that is not a
    ``str`` (or an iterable of ``str``) raises ``TypeError``; decode header bytes as
    ISO-8859-1 first.

    >>> from timingheader import parse
    >>> [(m.name, m.dur, m.desc) for m in parse('db;dur=53;desc="primary", cache;desc=d1 d2')]
    [('db', 53.0, 'primary'), ('cache', None, 'd1')]
    >>> [m.name for m in parse(["miss, db;dur=53", "total;dur=123.4"])]
    ['miss', 'db', 'total']
    >>> parse("db;dur=1, [x], a;DUR=2;dur=3", strict=False)[1].dur
    2.0
    """
    return _parse_values(header, strict=strict)


# ``Iterable`` is not a name of the package, so its annotations resolve where the work is
# done: typing.get_type_hints and inspect.signature(eval_str=True) follow ``__wrapped__``.
_functools.update_wrapper(parse, _parse_values, assigned=(), updated=())

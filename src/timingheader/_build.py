"""Render metrics into a Server-Timing header value that is safe to send."""

from __future__ import annotations

from collections.abc import Iterable

from ._errors import ServerTimingError, shown
from ._metric import Metric
from ._number import format_number
from ._syntax import ascii_lower, check_token, quote

_RESERVED = frozenset({"dur", "desc"})
MAX_PRECISION = 20


def build(metrics: Iterable[Metric], *, precision: int | None = None) -> str:
    """Join metrics into one header value such as ``db;dur=53, cache;desc="Cache Read"``.

    Raises ``ServerTimingError`` (a ``ValueError``) for a value that cannot be written
    safely: a name or parameter name that is not a token, a description or parameter value
    holding a character no HTTP field can carry (CR, LF, NUL and other controls), a
    duration that is not finite, or a repeated parameter. Raises ``TypeError`` for an
    argument of the wrong type: ``metrics`` a single ``Metric`` or a ``str``, an item that
    is not a ``Metric``, or a part of a metric that is not a ``str`` (or a real number for
    the duration). ``precision`` (an int from 0 to 20) rounds durations to that many
    decimal places, which keeps the header short; the default keeps every digit.

    >>> from timingheader import Metric, build
    >>> build([Metric("db", dur=53.25, desc="primary"), Metric("cdn", params=(("hit", "1"),))])
    'db;dur=53.25;desc=primary, cdn;hit=1'
    >>> build([Metric("db", dur=53.25)], precision=1)
    'db;dur=53.2'
    >>> from timingheader import ServerTimingError
    >>> try:
    ...     build([Metric("db", desc="a\\r\\nSet-Cookie: x=1")])
    ... except ServerTimingError as error:
    ...     print(error)
    description holds '\\r' at index 1, which no HTTP field value can carry
    """
    if precision is not None:
        if isinstance(precision, bool) or not isinstance(precision, int):
            raise TypeError(f"precision must be an int or None, got {shown(precision)}")
        if not 0 <= precision <= MAX_PRECISION:
            raise ServerTimingError(
                f"precision must be from 0 to {MAX_PRECISION}, got {shown(precision)}"
            )
    if isinstance(metrics, (Metric, str)):
        raise TypeError("build takes an iterable of metrics; wrap one metric in a list")
    return ", ".join(render(metric, precision) for metric in metrics)


def render(metric: Metric, precision: int | None = None) -> str:
    """Serialize one metric, checking every part of it."""
    if not isinstance(metric, Metric):
        raise TypeError(f"expected a Metric, got {shown(metric)}")
    parts = [check_token(metric.name, "metric name")]
    if metric.dur is not None:
        parts.append(f"dur={format_number(metric.dur, precision)}")
    if metric.desc is not None:
        parts.append(f"desc={_quote_str(metric.desc, 'description')}")
    seen: set[str] = set()
    for pair in metric.params:
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise TypeError(f"params must hold (name, value) pairs, got {shown(pair)}")
        name, value = pair
        key = ascii_lower(check_token(name, "parameter name"))
        if key in _RESERVED:
            raise ServerTimingError(f"parameter {shown(name)} belongs in Metric.dur or Metric.desc")
        if key in seen:
            raise ServerTimingError(f"parameter {shown(name)} is given more than once")
        seen.add(key)
        parts.append(f"{name}={_quote_str(value, f'parameter {shown(name)}')}")
    return ";".join(parts)


def _quote_str(value: str, what: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{what} must be a str, got {shown(value)}")
    return quote(value, what)

"""Render metrics into a Server-Timing header value that is safe to send."""

from __future__ import annotations

from collections.abc import Iterable

from ._errors import ServerTimingError
from ._metric import Metric
from ._number import format_number
from ._syntax import check_token, quote

_RESERVED = frozenset({"dur", "desc"})


def build(metrics: Iterable[Metric], *, precision: int | None = None) -> str:
    """Join metrics into one header value such as ``db;dur=53, cache;desc="Cache Read"``.

    Raises ``ServerTimingError`` (a ``ValueError``) for anything that cannot be written
    safely: a name or parameter name that is not a token, a description or parameter value
    holding a character no HTTP field can carry (CR, LF, NUL and other controls), or a
    duration that is not a finite number. ``precision`` rounds durations to that many
    decimal places, which keeps the header short; the default keeps every digit.
    """
    if precision is not None and (
        isinstance(precision, bool) or not isinstance(precision, int) or precision < 0
    ):
        raise ServerTimingError(f"precision must be a non-negative int, got {precision!r}")
    if isinstance(metrics, Metric):
        raise ServerTimingError("build takes an iterable of metrics; wrap one metric in a list")
    return ", ".join(render(metric, precision) for metric in metrics)


def render(metric: Metric, precision: int | None = None) -> str:
    """Serialize one metric, checking every part of it."""
    if not isinstance(metric, Metric):
        raise ServerTimingError(f"expected a Metric, got {metric!r}")
    parts = [check_token(metric.name, "metric name")]
    if metric.dur is not None:
        parts.append(f"dur={format_number(metric.dur, precision)}")
    if metric.desc is not None:
        parts.append(f"desc={_quote_str(metric.desc, 'description')}")
    seen: set[str] = set()
    for pair in metric.params:
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise ServerTimingError(f"params must hold (name, value) pairs, got {pair!r}")
        name, value = pair
        key = check_token(name, "parameter name").lower()
        if key in _RESERVED:
            raise ServerTimingError(f"parameter {name!r} belongs in Metric.dur or Metric.desc")
        if key in seen:
            raise ServerTimingError(f"parameter {name!r} is given more than once")
        seen.add(key)
        parts.append(f"{name}={_quote_str(value, f'parameter {name!r}')}")
    return ";".join(parts)


def _quote_str(value: str, what: str) -> str:
    if not isinstance(value, str):
        raise ServerTimingError(f"{what} must be a str, got {value!r}")
    return quote(value, what)

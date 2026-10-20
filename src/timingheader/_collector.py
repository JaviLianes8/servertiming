"""Collect metrics during a request and emit them as a header value."""

from __future__ import annotations

import math
import threading
import time
from collections.abc import Callable

from ._build import build, render
from ._errors import ServerTimingError, shown
from ._metric import Metric


class Timing:
    """Gather metrics over the course of some work and render the header at the end.

    Durations are milliseconds read from ``clock``, ``time.perf_counter`` by default: a
    monotonic clock, so a wall-clock change cannot make a duration jump or go negative.
    Names and descriptions are checked when recorded, so a bad one fails at the call
    site instead of when the header is rendered: ``ServerTimingError`` for a value that
    cannot be sent, ``TypeError`` for one of the wrong type. Recording is safe from
    several threads. A clock reading that makes a duration infinite, NaN or too large for
    a float raises ``ServerTimingError`` where the measurement ends, and nothing is
    recorded for it.

    >>> import itertools
    >>> from timingheader import Timing
    >>> ticks = itertools.count(0.0, 0.25)  # a fake clock: 250 ms per reading
    >>> timing = Timing(clock=lambda: next(ticks))
    >>> with timing.measure("db", desc="query"):
    ...     pass
    >>> timing.header()
    'db;dur=250;desc=query'
    """

    def __init__(self, clock: Callable[[], float] = time.perf_counter) -> None:
        if not callable(clock):
            raise TypeError("clock must be a callable that returns seconds as a float")
        self._clock = clock
        self._metrics: list[Metric] = []
        self._lock = threading.Lock()

    def add(self, name: str, dur: float | None = None, desc: str | None = None) -> Metric:
        """Record a metric with an explicit duration (or none) and return it.

        >>> from timingheader import Timing
        >>> timing = Timing()
        >>> timing.add("cache", desc="miss")
        Metric(name='cache', dur=None, desc='miss', params=())
        >>> timing.add("db", 12.5).dur
        12.5
        """
        metric = Metric(name=name, dur=dur, desc=desc)
        render(metric)
        with self._lock:
            self._metrics.append(metric)
        return metric

    def measure(self, name: str, desc: str | None = None) -> Measure:
        """Time a ``with`` block, or every call of a decorated function, plain or async.

        The duration is recorded even when the block or the call raises. See ``Measure``.

        >>> import itertools
        >>> from timingheader import Timing
        >>> ticks = itertools.count(0.0, 0.002)
        >>> timing = Timing(clock=lambda: next(ticks))
        >>> @timing.measure("render")
        ... def render() -> str:
        ...     return "<html>"
        >>> render(), timing.header()
        ('<html>', 'render;dur=2')
        """
        return Measure(self, name, desc)

    def start(self, name: str, desc: str | None = None) -> Timer:
        """Start a timer for work that does not fit in one block; ``stop()`` records it.

        >>> import itertools
        >>> from timingheader import Timing
        >>> ticks = itertools.count(0.0, 0.5)
        >>> timing = Timing(clock=lambda: next(ticks))
        >>> timing.start("upload").stop()
        Metric(name='upload', dur=500.0, desc=None, params=())
        """
        return Timer(self, name, desc, self._clock())

    @property
    def metrics(self) -> list[Metric]:
        """A copy of the metrics recorded so far, in the order they finished.

        >>> from timingheader import Timing
        >>> timing = Timing()
        >>> _ = timing.add("a"), timing.add("b")
        >>> [metric.name for metric in timing.metrics]
        ['a', 'b']
        """
        with self._lock:
            return list(self._metrics)

    def header(self, *, precision: int | None = None) -> str:
        """Render every recorded metric into one Server-Timing header value.

        ``precision`` rounds durations as in ``build``.

        >>> from timingheader import Timing
        >>> timing = Timing()
        >>> _ = timing.add("db", 12.3456), timing.add("cache")
        >>> timing.header(precision=1)
        'db;dur=12.3, cache'
        """
        return build(self.metrics, precision=precision)

    def _finish(self, name: str, desc: str | None, start: float) -> Metric:
        # Read outside the guard: an OverflowError raised by the clock itself is its own error.
        now = self._clock()
        try:
            dur = (now - start) * 1000.0
        except OverflowError:
            # An int reading too large for a float: as unusable as an infinite one.
            dur = math.inf
        if not math.isfinite(dur):
            # Recorded, it would make every later header() fail and lose the other metrics.
            raise ServerTimingError(f"the clock gave a duration that is not finite: {shown(dur)}")
        metric = Metric(name=name, dur=dur, desc=desc)
        with self._lock:
            self._metrics.append(metric)
        return metric


# Imported last, once Timing exists: the annotations of Measure and Timer name Timing, so
# their module imports it at run time, and typing.get_type_hints can resolve them.
from ._measure import Measure, Timer  # noqa: E402

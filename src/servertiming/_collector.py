"""Collect metrics during a request and emit them as a header value."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager

from ._build import build
from ._metric import Metric


class Timing:
    """Gather metrics over the course of some work and render the header at the end.

    The clock is injectable so tests stay deterministic. ``measure`` times a block and
    records its duration in milliseconds, matching the header convention.
    """

    def __init__(self, clock: Callable[[], float] = time.perf_counter) -> None:
        self._clock = clock
        self._metrics: list[Metric] = []

    def add(self, name: str, dur: float | None = None, desc: str | None = None) -> Metric:
        """Record a metric with an explicit duration (or none)."""
        metric = Metric(name=name, dur=dur, desc=desc)
        self._metrics.append(metric)
        return metric

    @contextmanager
    def measure(self, name: str, desc: str | None = None) -> Iterator[None]:
        """Time the wrapped block and record its elapsed duration in milliseconds."""
        start = self._clock()
        try:
            yield
        finally:
            elapsed_ms = (self._clock() - start) * 1000.0
            self._metrics.append(Metric(name=name, dur=elapsed_ms, desc=desc))

    @property
    def metrics(self) -> list[Metric]:
        """A copy of the metrics recorded so far, in insertion order."""
        return list(self._metrics)

    def header(self) -> str:
        """Render every recorded metric into a single Server-Timing header value."""
        return build(self._metrics)

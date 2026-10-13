"""Collect metrics during a request and emit them as a header value."""

from __future__ import annotations

import functools
import inspect
import threading
import time
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, TypeVar, cast

from ._build import build, render
from ._metric import Metric

F = TypeVar("F", bound=Callable[..., Any])


class Timing:
    """Gather metrics over the course of some work and render the header at the end.

    Durations are milliseconds read from ``clock``, ``time.perf_counter`` by default: a
    monotonic clock, so a wall-clock change cannot make a duration jump or go negative.
    Names and descriptions are checked when recorded, so a bad one fails at the call
    site instead of when the header is rendered. Recording is safe from several threads.
    """

    def __init__(self, clock: Callable[[], float] = time.perf_counter) -> None:
        self._clock = clock
        self._metrics: list[Metric] = []
        self._lock = threading.Lock()

    def add(self, name: str, dur: float | None = None, desc: str | None = None) -> Metric:
        """Record a metric with an explicit duration (or none) and return it."""
        metric = Metric(name=name, dur=dur, desc=desc)
        render(metric)
        with self._lock:
            self._metrics.append(metric)
        return metric

    def measure(self, name: str, desc: str | None = None) -> Measure:
        """Time a ``with`` block, or every call of a decorated function, plain or async.

        The duration is recorded even when the block or the call raises.
        """
        render(Metric(name=name, dur=0.0, desc=desc))
        return Measure(self, name, desc)

    def start(self, name: str, desc: str | None = None) -> Timer:
        """Start a timer for work that does not fit in one block; ``stop()`` records it."""
        render(Metric(name=name, dur=0.0, desc=desc))
        return Timer(self, name, desc, self._clock())

    @property
    def metrics(self) -> list[Metric]:
        """A copy of the metrics recorded so far, in the order they finished."""
        with self._lock:
            return list(self._metrics)

    def header(self, *, precision: int | None = None) -> str:
        """Render every recorded metric into one Server-Timing header value."""
        return build(self.metrics, precision=precision)

    def _finish(self, name: str, desc: str | None, start: float) -> Metric:
        metric = Metric(name=name, dur=(self._clock() - start) * 1000.0, desc=desc)
        with self._lock:
            self._metrics.append(metric)
        return metric


class Measure:
    """What ``Timing.measure`` returns: a context manager and a function decorator."""

    def __init__(self, timing: Timing, name: str, desc: str | None) -> None:
        self._timing = timing
        self._name = name
        self._desc = desc
        # A context variable keeps the start times apart when one Measure is entered from
        # several threads or asyncio tasks at once; each sees only its own nesting.
        self._starts: ContextVar[tuple[float, ...]] = ContextVar("starts", default=())

    def __enter__(self) -> None:
        self._starts.set((*self._starts.get(), self._timing._clock()))

    def __exit__(self, *exc_info: object) -> None:
        *outer, start = self._starts.get()
        self._starts.set(tuple(outer))
        self._timing._finish(self._name, self._desc, start)

    def __call__(self, func: F) -> F:
        timing, name, desc = self._timing, self._name, self._desc
        if inspect.iscoroutinefunction(func):
            # Timing the call alone would only time creating the coroutine, not running it.
            @functools.wraps(func)
            async def run_async(*args: Any, **kwargs: Any) -> Any:
                start = timing._clock()
                try:
                    return await func(*args, **kwargs)
                finally:
                    timing._finish(name, desc, start)

            return cast(F, run_async)

        @functools.wraps(func)
        def run(*args: Any, **kwargs: Any) -> Any:
            start = timing._clock()
            try:
                return func(*args, **kwargs)
            finally:
                timing._finish(name, desc, start)

        return cast(F, run)


class Timer:
    """A running measurement returned by ``Timing.start``."""

    def __init__(self, timing: Timing, name: str, desc: str | None, start: float) -> None:
        self._timing = timing
        self._name = name
        self._desc = desc
        self._start = start
        self._metric: Metric | None = None
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        """Whether ``stop`` has not been called yet."""
        return self._metric is None

    def stop(self) -> Metric:
        """Record the elapsed milliseconds and return the metric; a timer stops once."""
        with self._lock:
            if self._metric is not None:
                raise RuntimeError(f"timer {self._name!r} is already stopped")
            self._metric = self._timing._finish(self._name, self._desc, self._start)
            return self._metric

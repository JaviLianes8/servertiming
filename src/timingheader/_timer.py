"""A running measurement held as an object, started and stopped by hand."""

from __future__ import annotations

import threading

from ._collector import Timing
from ._errors import shown
from ._measure import checked
from ._metric import Metric


class Timer:
    """A running measurement returned by ``Timing.start``; ``stop()`` records it once.

    Usually created by ``Timing.start``; the constructor checks its arguments the same way,
    and ``start`` must be a reading of the timing's clock.

    >>> import itertools
    >>> from timingheader import Timing
    >>> ticks = itertools.count(0.0, 0.1)
    >>> timing = Timing(clock=lambda: next(ticks))
    >>> timer = timing.start("upload", desc="s3")
    >>> timer.running
    True
    >>> timer.stop()
    Metric(name='upload', dur=100.0, desc='s3', params=())
    >>> timer.running
    False
    """

    def __init__(self, timing: Timing, name: str, desc: str | None, start: float) -> None:
        checked(timing, name, desc)
        if isinstance(start, bool) or not isinstance(start, (int, float)):
            raise TypeError(f"start must be a clock reading (a float), got {shown(start)}")
        self._timing = timing
        self._name = name
        self._desc = desc
        self._start = start
        self._metric: Metric | None = None
        self._lock = threading.Lock()

    @property
    def running(self) -> bool:
        """Whether ``stop`` has not been called yet.

        >>> from timingheader import Timing
        >>> timer = Timing(clock=lambda: 0.0).start("job")
        >>> timer.running, timer.stop().dur, timer.running
        (True, 0.0, False)
        """
        return self._metric is None

    def stop(self) -> Metric:
        """Record the elapsed milliseconds and return the metric.

        A timer stops once: a second call raises ``RuntimeError``. A clock reading that
        gives a duration that is not finite (or too large for a float) raises
        ``ServerTimingError``, records nothing and leaves the timer running.

        >>> import itertools
        >>> from timingheader import Timing
        >>> ticks = itertools.count(0.0, 0.004)
        >>> timing = Timing(clock=lambda: next(ticks))
        >>> timer = timing.start("render")
        >>> timer.stop()
        Metric(name='render', dur=4.0, desc=None, params=())
        >>> try:
        ...     timer.stop()
        ... except RuntimeError as error:
        ...     print(error)
        timer 'render' is already stopped
        """
        with self._lock:
            if self._metric is not None:
                raise RuntimeError(f"timer {shown(self._name)} is already stopped")
            self._metric = self._timing._finish(self._name, self._desc, self._start)
            return self._metric

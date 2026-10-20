"""Contracts for errors raised by the clock itself, from the third 1.0.0 QA round."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest

from timingheader import Timing


class ClockBroke(Exception):
    pass


def _clock(first: float, error: Exception) -> Callable[[], float]:
    readings: Iterator[float] = iter([first])

    def clock() -> float:
        try:
            return next(readings)
        except StopIteration:
            raise error from None

    return clock


@pytest.mark.parametrize("error", [OverflowError("backend overflowed"), ClockBroke("gone")])
def test_an_error_from_the_clock_reaches_the_caller_of_stop(error: Exception) -> None:
    timing = Timing(clock=_clock(0.0, error))
    timer = timing.start("a")
    with pytest.raises(type(error)) as raised:
        timer.stop()
    assert raised.value is error
    assert timer.running
    assert timing.metrics == []


@pytest.mark.parametrize("error", [OverflowError("backend overflowed"), ClockBroke("gone")])
def test_an_error_from_the_clock_reaches_the_caller_of_a_block(error: Exception) -> None:
    timing = Timing(clock=_clock(0.0, error))
    with pytest.raises(type(error)) as raised, timing.measure("a"):
        pass
    assert raised.value is error
    assert timing.metrics == []


def test_an_error_from_the_clock_reaches_the_caller_of_a_decorated_function() -> None:
    error = OverflowError("backend overflowed")
    timing = Timing(clock=_clock(0.0, error))

    @timing.measure("a")
    def work() -> int:
        return 1

    with pytest.raises(OverflowError) as raised:
        work()
    assert raised.value is error
    assert timing.metrics == []

from __future__ import annotations

import asyncio
import threading
import time

import pytest

from timingheader import Metric, ServerTimingError, Timing


def _ticks(*values: float) -> Timing:
    it = iter(values)
    return Timing(clock=lambda: next(it))


def test_add_records_a_metric() -> None:
    timing = Timing()
    assert timing.add("db", dur=2.0, desc="query") == Metric("db", dur=2.0, desc="query")
    assert timing.metrics == [Metric("db", dur=2.0, desc="query")]


@pytest.mark.parametrize(
    ("name", "dur", "desc"), [("bad name", None, None), ("db", float("nan"), None), ("db", 1, "\n")]
)
def test_add_rejects_what_cannot_be_sent_at_the_call(name: str, dur: float, desc: str) -> None:
    timing = Timing()
    with pytest.raises(ServerTimingError):
        timing.add(name, dur, desc)
    assert timing.metrics == []


def test_measure_records_elapsed_milliseconds_with_an_injected_clock() -> None:
    timing = _ticks(1.0, 1.25)
    with timing.measure("work", desc="html"):
        pass
    assert timing.metrics == [Metric("work", dur=250.0, desc="html")]


def test_measure_records_even_when_the_block_raises() -> None:
    timing = _ticks(0.0, 0.5)
    with pytest.raises(RuntimeError), timing.measure("work"):
        raise RuntimeError("boom")
    assert timing.metrics == [Metric("work", dur=500.0)]


def test_measure_checks_the_name_before_the_block_runs() -> None:
    timing = Timing()
    with pytest.raises(ServerTimingError):
        timing.measure("bad name")
    with pytest.raises(ServerTimingError):
        timing.start("db", desc="\r")


def test_nested_measures_record_inner_first() -> None:
    timing = _ticks(0.0, 0.25, 0.75, 1.0)
    with timing.measure("outer"), timing.measure("inner"):
        pass
    assert timing.metrics == [Metric("inner", dur=500.0), Metric("outer", dur=1000.0)]


def test_measure_decorates_a_function_and_times_every_call() -> None:
    timing = _ticks(0.0, 0.002, 1.0, 1.004)

    @timing.measure("work")
    def work(x: int) -> int:
        """Doubles."""
        return x * 2

    assert (work(2), work(3)) == (4, 6)
    assert work.__name__ == "work"
    assert work.__doc__ == "Doubles."
    assert [m.dur for m in timing.metrics] == pytest.approx([2.0, 4.0])


def test_a_decorated_function_records_even_when_it_raises() -> None:
    timing = _ticks(0.0, 0.001)

    @timing.measure("work")
    def work() -> None:
        raise KeyError("x")

    with pytest.raises(KeyError):
        work()
    assert timing.metrics == [Metric("work", dur=1.0)]


def test_measure_decorates_a_coroutine_function_and_times_the_await() -> None:
    now = [0.0]
    timing = Timing(clock=lambda: now[0])

    @timing.measure("io")
    async def io() -> str:
        await asyncio.sleep(0)
        now[0] = 0.5  # time passes while the coroutine is suspended
        return "done"

    assert asyncio.run(io()) == "done"
    assert timing.metrics == [Metric("io", dur=500.0)]


def test_a_decorated_coroutine_records_even_when_it_raises() -> None:
    timing = _ticks(0.0, 0.003)

    @timing.measure("io")
    async def io() -> None:
        raise ValueError("x")

    with pytest.raises(ValueError):
        asyncio.run(io())
    assert timing.metrics == [Metric("io", dur=3.0)]


def test_start_returns_a_timer_that_records_on_stop() -> None:
    timing = _ticks(2.0, 2.5)
    timer = timing.start("render", desc="html")
    assert timer.running
    assert timing.metrics == []
    assert timer.stop() == Metric("render", dur=500.0, desc="html")
    assert not timer.running
    assert timing.metrics == [Metric("render", dur=500.0, desc="html")]


def test_a_timer_stops_only_once() -> None:
    timing = _ticks(0.0, 1.0, 2.0)
    timer = timing.start("x")
    timer.stop()
    with pytest.raises(RuntimeError, match="already stopped"):
        timer.stop()
    assert len(timing.metrics) == 1


def test_the_default_clock_is_monotonic_perf_counter() -> None:
    assert Timing()._clock is time.perf_counter
    assert time.get_clock_info("perf_counter").monotonic


def test_header_renders_the_recorded_metrics_with_precision() -> None:
    timing = _ticks(0.0, 0.0123456)
    timing.add("app", dur=5.0)
    with timing.measure("db", desc="query"):
        pass
    assert timing.header() == "app;dur=5, db;dur=12.3456;desc=query"
    assert timing.header(precision=1) == "app;dur=5, db;dur=12.3;desc=query"


def test_metrics_property_returns_a_copy() -> None:
    timing = Timing()
    timing.add("db", dur=1.0)
    snapshot = timing.metrics
    timing.add("cache", dur=2.0)
    assert snapshot == [Metric("db", dur=1.0)]


def test_recording_from_many_threads_loses_nothing() -> None:
    timing = Timing()

    def work() -> None:
        for _ in range(500):
            with timing.measure("t"):
                pass

    threads = [threading.Thread(target=work) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(timing.metrics) == 4000

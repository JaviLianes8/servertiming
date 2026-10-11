import pytest

from servertiming import Metric, Timing


def test_add_records_a_metric() -> None:
    timing = Timing()
    timing.add("db", dur=2.0, desc="query")
    assert timing.metrics == [Metric("db", dur=2.0, desc="query")]


def test_measure_records_elapsed_milliseconds_with_an_injected_clock() -> None:
    ticks = iter([1.0, 1.25])
    timing = Timing(clock=lambda: next(ticks))
    with timing.measure("work"):
        pass
    assert timing.metrics == [Metric("work", dur=250.0)]


def test_measure_keeps_the_description() -> None:
    ticks = iter([0.0, 0.1])
    timing = Timing(clock=lambda: next(ticks))
    with timing.measure("render", desc="html"):
        pass
    assert timing.metrics[0].desc == "html"


def test_measure_records_even_when_the_block_raises() -> None:
    ticks = iter([0.0, 0.5])
    timing = Timing(clock=lambda: next(ticks))
    with pytest.raises(RuntimeError), timing.measure("work"):
        raise RuntimeError("boom")
    assert timing.metrics[0].dur == 500.0


def test_real_clock_produces_a_non_negative_duration() -> None:
    timing = Timing()
    with timing.measure("work"):
        pass
    dur = timing.metrics[0].dur
    assert dur is not None
    assert dur >= 0.0


def test_header_renders_the_recorded_metrics() -> None:
    timing = Timing()
    timing.add("app", dur=5.0)
    timing.add("db", dur=2.0, desc="query")
    assert timing.header() == "app;dur=5, db;dur=2;desc=query"


def test_metrics_property_returns_a_copy() -> None:
    timing = Timing()
    timing.add("db", dur=1.0)
    snapshot = timing.metrics
    timing.add("cache", dur=2.0)
    assert snapshot == [Metric("db", dur=1.0)]

"""Contracts for the recording helpers and the public surface, from the 1.0.0 QA round."""

from __future__ import annotations

import contextvars
import gc
import inspect
import math
import pickle
import threading
import weakref
from collections.abc import Callable

import pytest

import timingheader
from timingheader import Measure, Metric, ServerTimingError, Timer, Timing, build, parse


def _many_measures(count: int) -> int:
    for _ in range(count):
        timing = Timing()
        with timing.measure("db"):
            pass
        timing.header()
    return len(contextvars.copy_context())


def test_measure_leaves_no_context_variable_behind_in_a_long_lived_context() -> None:
    assert contextvars.Context().run(_many_measures, 2_000) <= 1


def test_measure_leaves_no_context_variable_behind_in_a_worker_thread() -> None:
    sizes: list[int] = []
    worker = threading.Thread(target=lambda: sizes.append(_many_measures(2_000)))
    worker.start()
    worker.join()
    assert sizes and sizes[0] <= 1 + len(contextvars.copy_context())


def test_a_finished_measure_is_not_kept_alive() -> None:
    measure = Timing().measure("a")
    with measure:
        pass
    ref = weakref.ref(measure)
    del measure
    gc.collect()
    assert ref() is None


def test_an_exit_without_a_matching_enter_raises_runtime_error() -> None:
    timing = Timing()
    measure = timing.measure("a")
    with pytest.raises(RuntimeError, match="without a matching enter"):
        measure.__exit__(None, None, None)
    measure.__enter__()
    caught: list[BaseException] = []

    def leave() -> None:
        try:
            measure.__exit__(None, None, None)
        except BaseException as error:
            caught.append(error)

    worker = threading.Thread(target=leave)
    worker.start()
    worker.join()
    assert len(caught) == 1 and isinstance(caught[0], RuntimeError)
    measure.__exit__(None, None, None)
    assert [m.name for m in timing.metrics] == ["a"]


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_a_clock_that_gives_a_non_finite_duration_fails_where_it_is_read(bad: float) -> None:
    readings = iter([0.0, bad, 0.0, bad])
    timing = Timing(clock=lambda: next(readings))
    with pytest.raises(ServerTimingError, match="finite"), timing.measure("a"):
        pass
    timer = timing.start("b")
    with pytest.raises(ServerTimingError, match="finite"):
        timer.stop()
    timing.add("c", 1.0)
    assert timing.header() == "c;dur=1"


def _not_a_timing() -> Timing:
    return object()  # type: ignore[return-value]


@pytest.mark.parametrize(
    ("call", "error"),
    [
        (lambda: Measure(Timing(), "bad name", None), ServerTimingError),
        (lambda: Measure(Timing(), "a", "x\r\nSet-Cookie: y=1"), ServerTimingError),
        (lambda: Measure(Timing(), 42, None), TypeError),  # type: ignore[arg-type]
        (lambda: Measure(_not_a_timing(), "a", None), TypeError),
        (lambda: Timer(Timing(), 42, None, 0.0), TypeError),  # type: ignore[arg-type]
        (lambda: Timer(Timing(), "a", "x\ny", 0.0), ServerTimingError),
        (lambda: Timer(_not_a_timing(), "a", None, 0.0), TypeError),
        (lambda: Timer(Timing(), "a", None, "0"), TypeError),  # type: ignore[arg-type]
        (lambda: Timer(Timing(clock=lambda: 2.0), "a", None, True), TypeError),
    ],
)
def test_the_measure_and_timer_constructors_check_what_they_record(
    call: Callable[[], object], error: type[Exception]
) -> None:
    with pytest.raises(error):
        call()


def test_measure_and_timer_built_directly_record_like_the_collector_methods() -> None:
    readings = iter([0.0, 0.5, 1.0, 1.25])
    timing = Timing(clock=lambda: next(readings))
    with Measure(timing, "a", "x"):
        pass
    Timer(timing, "b", None, timing._clock()).stop()
    assert timing.header() == "a;dur=500;desc=x, b;dur=250"


class _Sneaky(str):
    """A str whose iteration and formatting hide its real text."""

    __slots__ = ()

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter("ok")

    def __format__(self, spec: str) -> str:
        return "ok"


@pytest.mark.parametrize(
    "call",
    [
        lambda: build([Metric(_Sneaky("db\r\nSet-Cookie: a=1"))]),
        lambda: str(Metric("db", desc=_Sneaky("x\r\nLocation: http://evil"))),
        lambda: build([Metric("db", params=(("hit", _Sneaky("1\r\nX: y")),))]),
        lambda: Timing().add(_Sneaky("db\r\nSet-Cookie: session=evil"), 1.0),
        lambda: Timing().measure("db", desc=_Sneaky("a\nb")),
        lambda: parse(_Sneaky("db\r\nX: y"), strict=True),
    ],
)
def test_a_str_subclass_cannot_smuggle_a_line_break(call: Callable[[], object]) -> None:
    with pytest.raises(ServerTimingError):
        call()


def test_a_str_subclass_is_written_as_its_real_text() -> None:
    metric = Metric(_Sneaky("db"), desc=_Sneaky("primary"), params=(("hit", _Sneaky("yes")),))
    assert str(metric) == "db;desc=primary;hit=yes"
    assert type(build([metric])) is str


def test_the_package_exposes_no_public_name_outside_all() -> None:
    extra = [
        n for n in dir(timingheader) if not n.startswith("_") and n not in timingheader.__all__
    ]
    assert extra == []


def _functions_of(cls: type) -> list[object]:
    found: list[object] = []
    for member in vars(cls).values():
        if isinstance(member, property):
            found.extend(f for f in (member.fget, member.fset, member.fdel) if f is not None)
        elif callable(member):
            found.append(member)
    return found


def test_every_public_callable_reports_the_package_as_its_module() -> None:
    for name in timingheader.__all__:
        obj = getattr(timingheader, name)
        assert obj.__module__ == "timingheader", name
        if inspect.isclass(obj):
            for member in _functions_of(obj):
                module = str(getattr(member, "__module__", ""))
                assert not module.startswith("timingheader."), (name, member)
    for func in (timingheader.build, timingheader.parse):
        data = pickle.dumps(func)
        assert b"timingheader._" not in data
        assert pickle.loads(data) is func

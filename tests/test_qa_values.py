"""Contracts for metric values, durations and error messages, from the 1.0.0 QA lenses."""

from __future__ import annotations

import math
from collections.abc import Callable

import pytest

from timingheader import Metric, ServerTimingError, Timing, build, parse


@pytest.mark.parametrize(
    ("dur", "text"),
    [
        (1e16, "1e16"),
        (1e-05, "1e-5"),
        (1.5e-07, "1.5e-7"),
        (-2.5e-100, "-2.5e-100"),
        (1e300, "1e300"),
    ],
)
def test_an_exponent_is_written_without_plus_sign_or_leading_zeros(dur: float, text: str) -> None:
    header = build([Metric("a", dur=dur)])
    assert header == f"a;dur={text}"
    assert parse(header, strict=True) == [Metric("a", dur=dur)]


@pytest.mark.parametrize("value", [10**400, -(10**5000)], ids=["big", "huge-negative"])
def test_an_int_duration_beyond_the_float_range_is_stored_as_an_infinity(value: int) -> None:
    metric = Metric("a", dur=value)
    assert isinstance(metric.dur, float) and math.isinf(metric.dur)
    assert (metric.dur > 0) == (value > 0)
    assert isinstance(metric.duration, float)
    assert "inf" in repr(metric)
    with pytest.raises(ServerTimingError, match="duration must be a finite number"):
        build([metric])


@pytest.mark.parametrize(
    "params",
    ["ab", [(1, "v")], [("a",)], [("a", "1", "2")], ["ab"], [None]],
)
def test_param_raises_type_error_for_malformed_params(params: object) -> None:
    metric = Metric("a", params=params)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="params must hold"):
        metric.param("a")


class _Precision(int):
    def __le__(self, other: object) -> bool:
        return True

    def __ge__(self, other: object) -> bool:
        return True

    def __format__(self, spec: str) -> str:
        raise AssertionError("the subclass hook was used")


def test_an_int_subclass_precision_is_used_as_its_exact_value() -> None:
    timing = Timing()
    timing.add("a", 1.25)
    for value in (10**8, -1, 21):
        with pytest.raises(ServerTimingError, match="precision must be from 0 to 20"):
            build([Metric("a", 1.0)], precision=_Precision(value))
        with pytest.raises(ServerTimingError, match="precision must be from 0 to 20"):
            timing.header(precision=_Precision(value))
    assert build([Metric("a", 1.25)], precision=_Precision(1)) == "a;dur=1.2"
    assert timing.header(precision=_Precision(1)) == "a;dur=1.2"


class _NoAbs(int):
    def __abs__(self) -> int:
        raise RuntimeError("hook ran")

    def bit_length(self) -> int:
        raise RuntimeError("hook ran")


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: build([Metric(_NoAbs(5))]), "metric name must be a str"),  # type: ignore[arg-type]
        (lambda: build([Metric("a", desc=_NoAbs(5))]), "description must be a str"),  # type: ignore[arg-type]
        (lambda: Metric("a").param(_NoAbs(1)), "parameter name must be a str"),  # type: ignore[arg-type]
        (lambda: Timing().add(_NoAbs(1)), "metric name must be a str"),  # type: ignore[arg-type]
        (lambda: build([Metric(_NoAbs(10**70))]), "an int of 233 bits"),  # type: ignore[arg-type]
    ],
)
def test_an_int_subclass_cannot_break_the_error_message(
    call: Callable[[], object], message: str
) -> None:
    with pytest.raises(TypeError, match=message):
        call()


@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda: build([Metric(5)]), "^metric name must be a str, got 5$"),  # type: ignore[arg-type]
        (
            lambda: build([Metric("db", params=((None, "1"),))]),  # type: ignore[arg-type]
            "^parameter name must be a str, got None$",
        ),
        (lambda: Timing().add(b"db"), "^metric name must be a str, got b'db'$"),  # type: ignore[arg-type]
        (lambda: Timing().measure(7), "^metric name must be a str, got 7$"),  # type: ignore[arg-type]
    ],
)
def test_a_name_that_is_not_a_str_is_named_in_the_type_error(
    call: Callable[[], object], message: str
) -> None:
    with pytest.raises(TypeError, match=message):
        call()

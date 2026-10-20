"""Contracts for what the Metric constructor stores and what param reads, from the QA lenses."""

from __future__ import annotations

import enum
import math
from collections.abc import Sequence
from http import HTTPStatus

import pytest

from timingheader import Metric, ServerTimingError, build


class _Int(int):
    pass


class _HookedInt(int):
    # Every hook lies: the stored duration must come from the exact int value alone.
    def __float__(self) -> float:
        return 99.0

    def __index__(self) -> int:
        return 99

    def __int__(self) -> int:
        return 99

    def __gt__(self, other: object) -> bool:
        return True

    def __repr__(self) -> str:
        raise AssertionError("the subclass hook was used")


class _Level(enum.IntEnum):
    SLOW = 250


@pytest.mark.parametrize(
    ("dur", "expected"),
    [
        (HTTPStatus.OK, 200.0),
        (_Level.SLOW, 250.0),
        (_Int(5), 5.0),
        (_HookedInt(7), 7.0),
        (_HookedInt(-(10**400)), -math.inf),
        (_Int(10**400), math.inf),
        (_Int(-(10**5000)), -math.inf),
        (_Int(10**5000), math.inf),
    ],
    ids=["httpstatus", "intenum", "subclass", "hooks", "hooks-huge", "big", "-huge", "huge"],
)
def test_an_int_subclass_duration_is_stored_as_a_float(dur: int, expected: float) -> None:
    metric = Metric("a", dur)
    assert type(metric.dur) is float and metric.dur == expected
    assert type(metric.duration) is float and metric.duration == expected
    assert repr(metric) == f"Metric(name='a', dur={expected!r}, desc=None, params=())"
    if math.isfinite(expected):
        assert build([metric]) == f"a;dur={int(expected)}"
    else:
        with pytest.raises(ServerTimingError, match="duration must be a finite number"):
            build([metric])


@pytest.mark.parametrize("zero", [0, _Int(0), _HookedInt(0)], ids=["int", "subclass", "hooks"])
def test_a_zero_int_duration_is_stored_as_a_float(zero: int) -> None:
    metric = Metric("a", zero)
    assert type(metric.dur) is float and metric.dur == 0.0
    assert repr(metric) == "Metric(name='a', dur=0.0, desc=None, params=())"


def test_a_bool_duration_is_kept_for_build_to_refuse() -> None:
    metric = Metric("a", True)
    assert metric.dur is True
    with pytest.raises(TypeError, match="duration must be an int or a float"):
        build([metric])


@pytest.mark.parametrize(
    "params",
    [[("A", "1"), 5], [("A", "1"), ("B", "2", "x")], (("A", "1"), None)],
    ids=["int", "triple", "none"],
)
def test_params_mixing_pairs_and_other_items_are_stored_unchanged(params: Sequence[object]) -> None:
    metric = Metric("a", params=params)  # type: ignore[arg-type]
    assert metric.params == tuple(params)


def test_param_matches_any_case_before_reaching_an_item_that_is_not_a_pair() -> None:
    metric = Metric("a", params=(("A", "1"), 5))  # type: ignore[arg-type]
    assert metric.params[0] == ("A", "1")
    assert metric.param("a") == "1"
    assert metric.param("A") == "1"
    with pytest.raises(TypeError, match=r"params must hold \(name, value\) pairs, got 5"):
        metric.param("b")


def test_param_on_params_that_are_not_a_tuple_raises_the_documented_error() -> None:
    with pytest.raises(TypeError, match=r"params must hold \(name, value\) pairs, got None"):
        Metric("a", params=None).param("x")  # type: ignore[arg-type]
    pairs = Metric("a", params={("k", "1")})  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="params must hold"):
        pairs.param("k")


def test_a_list_shaped_pair_is_not_a_pair() -> None:
    metric = Metric("a", params=[["A", "1"]])  # type: ignore[list-item]
    assert metric.params == (["A", "1"],)  # type: ignore[comparison-overlap]
    message = r"params must hold \(name, value\) pairs, got \['A', '1'\]"
    with pytest.raises(TypeError, match=message):
        metric.param("a")
    with pytest.raises(TypeError, match=message):
        build([metric])

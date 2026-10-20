"""The complete promise of every public name: signature, result and failure types."""

from __future__ import annotations

import dataclasses
import doctest
import inspect
import pickle
from collections.abc import Callable

import pytest

import timingheader
from timingheader import Measure, Metric, ServerTimingError, Timer, Timing, build, parse

SIGNATURES = {
    "build": "(metrics: 'Iterable[Metric]', *, precision: 'int | None' = None) -> 'str'",
    "parse": "(header: 'str | Iterable[str]', *, strict: 'bool' = False) -> 'list[Metric]'",
    "Timing.add": "(self, name: 'str', dur: 'float | None' = None, desc: 'str | None' = None)"
    " -> 'Metric'",
    "Timing.measure": "(self, name: 'str', desc: 'str | None' = None) -> 'Measure'",
    "Timing.start": "(self, name: 'str', desc: 'str | None' = None) -> 'Timer'",
    "Timing.header": "(self, *, precision: 'int | None' = None) -> 'str'",
    "Metric.param": "(self, name: 'str') -> 'str | None'",
    "Timer.stop": "(self) -> 'Metric'",
    "ServerTimingError.__init__": "(self, message: 'str', position: 'int | None' = None, "
    "field: 'int | None' = None) -> 'None'",
}


def _resolve(path: str) -> Callable[..., object]:
    target: object = timingheader
    for part in path.split("."):
        target = getattr(target, part)
    assert callable(target)
    return target


@pytest.mark.parametrize("path", sorted(SIGNATURES))
def test_signatures_are_pinned(path: str) -> None:
    assert str(inspect.signature(_resolve(path))) == SIGNATURES[path]


def test_the_default_clock_is_perf_counter() -> None:
    import time

    default = inspect.signature(Timing).parameters["clock"].default
    assert default is time.perf_counter


def test_metric_is_a_frozen_dataclass_with_pinned_fields() -> None:
    fields = [(f.name, f.default) for f in dataclasses.fields(Metric)]
    assert fields == [("name", dataclasses.MISSING), ("dur", None), ("desc", None), ("params", ())]
    metric = Metric("db", 1, "x", [("A", "1")])
    with pytest.raises(dataclasses.FrozenInstanceError):
        metric.name = "other"  # type: ignore[misc]
    assert pickle.loads(pickle.dumps(metric)) == metric
    assert hash(metric) == hash(Metric("db", 1.0, "x", (("a", "1"),)))


def test_public_classes_live_at_the_package_top() -> None:
    for cls in (Measure, Metric, ServerTimingError, Timer, Timing):
        assert cls.__module__ == "timingheader"
    assert b"_metric" not in pickle.dumps(Metric("a"))
    assert b"_errors" not in pickle.dumps(ServerTimingError("x", 1, 2))


def test_every_public_name_is_documented_with_an_example() -> None:
    for name in timingheader.__all__:
        assert ">>> " in (inspect.getdoc(getattr(timingheader, name)) or ""), name
    members = {
        Timing: ("add", "measure", "start", "metrics", "header"),
        Metric: ("duration", "description", "param", "__str__"),
    }
    for cls, names in members.items():
        for member in names:
            assert ">>> " in (inspect.getdoc(getattr(cls, member)) or ""), member


def test_doctests_of_the_public_classes_are_found_at_the_package_top() -> None:
    found = [t for t in doctest.DocTestFinder().find(timingheader) if t.examples]
    names = {t.name.removeprefix("timingheader.") for t in found}
    assert {"Metric", "Metric.param", "Timing", "Timing.add", "Measure", "Timer"} <= names
    assert {"ServerTimingError", "parse", "Timing.header"} <= names


def test_the_error_is_a_value_error_with_position_and_field_that_pickles() -> None:
    error = ServerTimingError("bad", 3, 1)
    assert isinstance(error, ValueError) and str(error) == "bad" and error.message == "bad"
    again = pickle.loads(pickle.dumps(error))
    assert (type(again), str(again), again.position, again.field) == (
        ServerTimingError,
        "bad",
        3,
        1,
    )
    assert (ServerTimingError("x").position, ServerTimingError("x").field) == (None, None)


def _gen() -> object:
    yield 1


async def _agen() -> object:
    yield 1


@pytest.mark.parametrize(
    "call",
    [
        lambda: parse(b"db"),  # type: ignore[arg-type]
        lambda: parse(["db", 1]),  # type: ignore[list-item]
        lambda: parse(None),  # type: ignore[arg-type]
        lambda: build(Metric("db")),  # type: ignore[arg-type]
        lambda: build("db"),  # type: ignore[arg-type]
        lambda: build([None]),  # type: ignore[list-item]
        lambda: build([Metric(1)]),  # type: ignore[arg-type]
        lambda: build([Metric("db", dur="5")]),  # type: ignore[arg-type]
        lambda: build([Metric("db", dur=True)]),
        lambda: build([Metric("db", desc=b"x")]),  # type: ignore[arg-type]
        lambda: build([Metric("db", params=(("a", 1),))]),  # type: ignore[arg-type]
        lambda: build([Metric("db", params=(("a",),))]),  # type: ignore[arg-type]
        lambda: build([Metric("db")], precision=2.0),  # type: ignore[arg-type]
        lambda: build([Metric("db")], precision=False),
        lambda: Metric("db").param(None),  # type: ignore[arg-type]
        lambda: str(Metric(None)),  # type: ignore[arg-type]
        lambda: Timing(clock=1.0),  # type: ignore[arg-type]
        lambda: Timing().add(1),  # type: ignore[arg-type]
        lambda: Timing().add("db", dur="1"),  # type: ignore[arg-type]
        lambda: Timing().measure("db", desc=1),  # type: ignore[arg-type]
        lambda: Timing().start(None),  # type: ignore[arg-type]
        lambda: Timing().measure("db")(1),  # type: ignore[type-var]
        lambda: Timing().measure("db")(_gen),
        lambda: Timing().measure("db")(_agen),
    ],
)
def test_wrong_argument_types_raise_type_error(call: Callable[[], object]) -> None:
    with pytest.raises(TypeError):
        call()


@pytest.mark.parametrize(
    "call",
    [
        lambda: parse("db;dur=x", strict=True),
        lambda: parse(["ok", "a,,b"], strict=True),
        lambda: build([Metric("bad name")]),
        lambda: build([Metric("db", dur=float("nan"))]),
        lambda: build([Metric("db", dur=10**400)]),
        lambda: build([Metric("db", desc="\n")]),
        lambda: build([Metric("db", params=(("dur", "1"),))]),
        lambda: build([Metric("db", params=(("a", "1"), ("A", "2")))]),
        lambda: build([Metric("db", params=((chr(0x212A), "1"),))]),
        lambda: build([Metric("db")], precision=21),
        lambda: build([Metric("db")], precision=-1),
        lambda: str(Metric("db", desc="\x7f")),
        lambda: Timing().add("bad name"),
        lambda: Timing().measure("db", desc="\r"),
        lambda: Timing().start("db", desc="☃"),
    ],
)
def test_invalid_values_raise_server_timing_error(call: Callable[[], object]) -> None:
    with pytest.raises(ServerTimingError):
        call()


def test_lenient_parse_never_raises_on_text() -> None:
    assert parse("") == [] and parse([]) == [] and parse(';,;="\\') == []

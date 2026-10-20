"""Hostile input: no blowup on large values, bounded error messages, odd objects."""

from __future__ import annotations

import time
from collections.abc import Callable

import pytest

from timingheader import Metric, ServerTimingError, Timing, build, parse
from timingheader._cli import fields_from_lines

SHAPES: dict[str, Callable[[int], str]] = {
    "semicolons": lambda n: "a" + ";" * n,
    "commas": lambda n: "," * n,
    "quotes": lambda n: '"' * n,
    "open quotes in params": lambda n: 'a;desc="' * (n // 8),
    "escapes": lambda n: 'a;desc="' + "\\" * n,
    "escaped quotes": lambda n: 'a;desc="' + '\\"' * (n // 2),
    "long token": lambda n: "a" * n,
    "many params": lambda n: "a" + ";x=1" * (n // 4),
    "repeated params": lambda n: "a" + ";dur=1" * (n // 6),
    "many metrics": lambda n: "a;dur=1, " * (n // 9),
    "long number": lambda n: "a;dur=" + "1" * n,
    "long exponent": lambda n: "a;dur=1e" + "9" * n,
    "long fraction": lambda n: "a;dur=0." + "0" * n + "1",
    "junk after value": lambda n: "a;dur=1" + " x" * (n // 2),
    "equals": lambda n: "a;" + "=" * n,
    "whitespace": lambda n: "a" + " \t" * (n // 2) + ";dur=1",
}


def _seconds(call: Callable[[], object]) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        call()
        best = min(best, time.perf_counter() - start)
    return best


def _strict(text: str) -> None:
    try:
        parse(text, strict=True)
    except ServerTimingError as error:
        assert len(str(error)) < 300


@pytest.mark.parametrize("shape", sorted(SHAPES))
def test_both_parsers_take_linear_time(shape: str) -> None:
    small, large = SHAPES[shape](50_000), SHAPES[shape](200_000)
    for read in (parse, _strict):
        slow = _seconds(lambda read=read: read(large))  # type: ignore[misc]
        ratio = slow / max(_seconds(lambda read=read: read(small)), 1e-4)  # type: ignore[misc]
        assert ratio < 10, (shape, read, ratio)


def test_the_command_reads_many_folded_lines_in_linear_time() -> None:
    def lines(n: int) -> list[str]:
        return ["HTTP/1.1 200 OK", "Server-Timing: a"] + [" ;x=1"] * n

    small, large = lines(50_000), lines(200_000)
    ratio = _seconds(lambda: fields_from_lines(large)) / _seconds(lambda: fields_from_lines(small))
    assert ratio < 10
    assert fields_from_lines(small)[0].count(";x=1") == 50_000


HUGE = "x" * 1_000_000


@pytest.mark.parametrize(
    "call",
    [
        lambda: build([Metric(HUGE + " ")]),
        lambda: build([Metric("a", desc=HUGE + "\n")]),
        lambda: build([Metric("a", params=((HUGE, "1"), (HUGE, "2")))]),
        lambda: build([Metric("a", params=((HUGE + " ", "1"),))]),
        lambda: build([Metric("a", params=(("x", HUGE + "\r"),))]),
        lambda: build([Metric("a", dur=10**100_000)]),
        lambda: build([Metric("a")], precision=10**100_000),
        lambda: parse("a;" + HUGE + "=1;" + HUGE + "=2", strict=True),
        lambda: parse("a;dur=" + HUGE, strict=True),
        lambda: parse("a" + HUGE + ";", strict=True),
        lambda: Timing().add(HUGE + ","),
    ],
)
def test_error_messages_stay_short_for_huge_values(call: Callable[[], object]) -> None:
    with pytest.raises(ServerTimingError) as caught:
        call()
    assert len(str(caught.value)) < 300


class _Unprintable:
    def __repr__(self) -> str:
        raise RuntimeError("no repr")


@pytest.mark.parametrize(
    "call",
    [
        lambda: build([_Unprintable()]),  # type: ignore[list-item]
        lambda: build([Metric("a", dur=_Unprintable())]),  # type: ignore[arg-type]
        lambda: build([Metric("a", desc=_Unprintable())]),  # type: ignore[arg-type]
        lambda: build([Metric("a")], precision=_Unprintable()),  # type: ignore[arg-type]
        lambda: parse([_Unprintable()]),  # type: ignore[list-item]
        lambda: build(["x" * 1_000_000]),  # type: ignore[list-item]
        lambda: Metric("a").param(_Unprintable()),  # type: ignore[arg-type]
    ],
)
def test_wrong_types_raise_type_error_with_a_short_message(call: Callable[[], object]) -> None:
    with pytest.raises(TypeError) as caught:
        call()
    assert len(str(caught.value)) < 300


def test_text_beyond_one_octet_is_read_but_never_written() -> None:
    for char in ("Ā", "\ud800", "\U0001f600"):
        (metric,) = parse(f'a;desc="{char}"')
        assert metric.desc == char
        with pytest.raises(ServerTimingError):
            build([metric])
        with pytest.raises(ServerTimingError):
            parse(f'a;desc="{char}"', strict=True)


def test_a_huge_int_is_described_by_its_size_not_written_out() -> None:
    for value in (10**60, 10**4400, -(10**100_000)):
        with pytest.raises(ServerTimingError, match=r"got an int of \d+ bits$"):
            build([Metric("a")], precision=value)
    with pytest.raises(ServerTimingError, match="got " + "9" * 60 + "$"):
        build([Metric("a")], precision=10**60 - 1)

"""Contracts for where a running block may end and what a clock may return, QA round 2."""

from __future__ import annotations

import asyncio
import contextlib
import contextvars
import inspect
import threading
import typing
from collections.abc import Callable

import pytest

import timingheader
from timingheader import ServerTimingError, Timer, Timing, parse


def _caught(call: Callable[[], object]) -> BaseException | None:
    try:
        call()
    except BaseException as error:
        return error
    return None


def test_an_exit_from_an_asyncio_task_that_copied_the_entry_raises() -> None:
    async def main() -> tuple[BaseException | None, list[str]]:
        timing = Timing()
        measure = timing.measure("x")
        measure.__enter__()

        async def child() -> BaseException | None:
            return _caught(lambda: measure.__exit__(None, None, None))

        error = await asyncio.create_task(child())
        measure.__exit__(None, None, None)
        return error, [m.name for m in timing.metrics]

    error, names = asyncio.run(main())
    assert isinstance(error, RuntimeError)
    assert names == ["x"]


def test_an_exit_from_to_thread_raises() -> None:
    async def main() -> tuple[BaseException | None, list[str]]:
        timing = Timing()
        measure = timing.measure("x")
        measure.__enter__()
        leave = (lambda: measure.__exit__(None, None, None),)
        error = await asyncio.to_thread(_caught, *leave)
        measure.__exit__(None, None, None)
        return error, [m.name for m in timing.metrics]

    error, names = asyncio.run(main())
    assert isinstance(error, RuntimeError)
    assert names == ["x"]


def test_a_thread_that_inherits_the_context_cannot_end_the_block() -> None:
    # What every new thread does on free-threaded 3.14 (thread_inherit_context).
    timing = Timing()
    measure = timing.measure("a")
    measure.__enter__()
    caught: list[BaseException | None] = []
    context = contextvars.copy_context()
    worker = threading.Thread(
        target=context.run, args=(lambda: caught.append(_caught(lambda: measure.__exit__())),)
    )
    worker.start()
    worker.join()
    assert len(caught) == 1 and isinstance(caught[0], RuntimeError)
    measure.__exit__(None, None, None)
    assert [m.name for m in timing.metrics] == ["a"]


def test_an_entry_ends_once_even_when_its_context_was_copied() -> None:
    timing = Timing()
    measure = timing.measure("x")
    measure.__enter__()
    contextvars.copy_context().run(measure.__exit__, None, None, None)
    with pytest.raises(RuntimeError, match="already"):
        measure.__exit__(None, None, None)
    assert [m.name for m in timing.metrics] == ["x"]
    with pytest.raises(RuntimeError, match="without a matching enter"):
        measure.__exit__(None, None, None)


def test_blocks_that_end_out_of_order_each_get_their_own_duration() -> None:
    timing = Timing(clock=iter([0.0, 1.0, 3.0, 6.0]).__next__)
    first, second = timing.measure("a"), timing.measure("b")
    first.__enter__()
    second.__enter__()
    first.__exit__(None, None, None)
    second.__exit__(None, None, None)
    assert timing.header() == "a;dur=3000, b;dur=5000"


def test_blocks_left_out_of_order_through_an_exit_stack_record_both() -> None:
    timing = Timing(clock=iter([0.0, 2.0, 3.0, 7.0]).__next__)
    with contextlib.ExitStack() as outer:
        outer.enter_context(timing.measure("a"))
        with contextlib.ExitStack() as inner:
            inner.enter_context(timing.measure("b"))
            outer.pop_all().close()
    assert timing.header() == "a;dur=3000, b;dur=5000"


@pytest.mark.parametrize(("start", "end"), [(10**400, 0.0), (0, 10**400), (0.0, -(10**400))])
def test_a_clock_reading_too_large_for_a_float_raises_the_documented_error(
    start: float, end: float
) -> None:
    timing = Timing(clock=lambda: end)
    timer = Timer(timing, "a", None, start)
    with pytest.raises(ServerTimingError, match="finite"):
        timer.stop()
    assert timer.running and timing.metrics == []
    readings = iter([start, end])
    blocks = Timing(clock=lambda: next(readings))
    with pytest.raises(ServerTimingError, match="finite"), blocks.measure("a"):
        pass
    assert blocks.metrics == []


def _public_callables() -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    for name in timingheader.__all__:
        obj = getattr(timingheader, name)
        if not inspect.isclass(obj):
            found.append((name, obj))
            continue
        for member_name, member in vars(obj).items():
            if isinstance(member, property):
                found.append((f"{name}.{member_name}", member.fget))
            elif inspect.isfunction(member):
                found.append((f"{name}.{member_name}", member))
    return found


@pytest.mark.parametrize(("name", "func"), _public_callables())
def test_every_public_annotation_resolves_at_run_time(name: str, func: object) -> None:
    typing.get_type_hints(func)
    inspect.signature(func, eval_str=True)  # type: ignore[arg-type]


class _Shouting(str):
    """A str whose length and indexing lie about its real text."""

    __slots__ = ()

    def __len__(self) -> int:
        return 2

    def __getitem__(self, index: typing.Any) -> str:
        return str.__getitem__(self, index).upper()


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("wrap", [lambda s: s, lambda s: [s]])
def test_parse_reads_the_real_text_of_a_str_subclass(
    strict: bool, wrap: Callable[[str], object]
) -> None:
    metrics = parse(wrap(_Shouting("db;dur=1, cache;desc=hit")), strict=strict)  # type: ignore[arg-type]
    assert [(m.name, m.dur, m.desc) for m in metrics] == [("db", 1.0, None), ("cache", None, "hit")]

"""Contracts for deep nesting and blocks left open, from the 1.0.0 QA lenses."""

from __future__ import annotations

import contextlib
import contextvars
import time
from collections.abc import Callable

from timingheader import Timing


def _seconds(call: Callable[[], object]) -> float:
    best = float("inf")
    for _ in range(3):
        start = time.perf_counter()
        call()
        best = min(best, time.perf_counter() - start)
    return best


def _nest(depth: int) -> None:
    measure = Timing(clock=lambda: 0.0).measure("a")
    with contextlib.ExitStack() as stack:
        for _ in range(depth):
            stack.enter_context(measure)


def test_nested_blocks_take_linear_time() -> None:
    # Copying the running entries on every enter and exit made this quadratic: 8 times the
    # depth took about 60 times as long.
    ratio = _seconds(lambda: _nest(16_000)) / max(_seconds(lambda: _nest(2_000)), 1e-4)
    assert ratio < 24, ratio


def _later_blocks_with_open_entries(open_entries: int) -> float:
    timing = Timing(clock=lambda: 0.0)
    left_open = timing.measure("open")
    for _ in range(open_entries):
        left_open.__enter__()
    later = timing.measure("later")

    def run() -> None:
        for _ in range(2_000):
            with later:
                pass

    return _seconds(run)


def test_blocks_left_open_do_not_slow_later_blocks() -> None:
    # Each run in a context of its own: the entries left open stay in the context they were
    # entered in.
    def run(open_entries: int) -> float:
        return contextvars.copy_context().run(_later_blocks_with_open_entries, open_entries)

    ratio = run(40_000) / max(run(0), 1e-4)
    assert ratio < 5, ratio


def test_entries_left_open_and_out_of_order_exits_still_record_each_block() -> None:
    contextvars.copy_context().run(_out_of_order)


def _out_of_order() -> None:
    timing = Timing(clock=iter(range(100)).__next__)
    outer, inner, other = timing.measure("outer"), timing.measure("inner"), timing.measure("x")
    outer.__enter__()  # 0
    inner.__enter__()  # 1
    other.__enter__()  # 2, never left
    outer.__exit__(None, None, None)  # 3
    inner.__exit__(None, None, None)  # 4
    assert [(m.name, m.dur) for m in timing.metrics] == [("outer", 3000.0), ("inner", 3000.0)]
    with inner:  # 5, 6
        pass
    assert timing.metrics[-1].dur == 1000.0


def test_an_outer_exit_keeps_the_order_of_the_entries_above_it() -> None:
    contextvars.copy_context().run(_outer_exit_under_two_entries)


def _outer_exit_under_two_entries() -> None:
    # The entries above an outer exit are rebuilt in their order, so a Measure entered twice
    # still pairs each exit with its own innermost enter.
    timing = Timing(clock=iter(range(100)).__next__)
    x, a, b = timing.measure("x"), timing.measure("a"), timing.measure("b")
    for measure in (x, a, b, a):  # 0, 1, 2, 3
        measure.__enter__()
    for measure in (x, a, b, a):  # 4, 5, 6, 7
        measure.__exit__(None, None, None)
    assert timing.header() == "x;dur=4000, a;dur=2000, b;dur=4000, a;dur=6000"

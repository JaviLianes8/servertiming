"""A running measurement held as a ``with`` block or a function decorator."""

from __future__ import annotations

import functools
import inspect
import sys
import threading
from collections.abc import Callable
from contextvars import ContextVar
from typing import Any, TypeAlias, TypeVar, cast

from ._build import render
from ._collector import Timing
from ._errors import shown
from ._metric import Metric

F = TypeVar("F", bound=Callable[..., Any])


class _Entry:
    """One running block: what entered it, when, and the thread and task that own it."""

    __slots__ = ("left", "measure", "owner", "start")

    def __init__(self, measure: Measure, start: float) -> None:
        self.measure = measure
        self.start = start
        self.owner = _owner()
        self.left = False


# The running entries of a context, newest first, as a linked stack of (entry, rest)
# pairs: entering and the usual innermost exit cost the same at any depth, and a copied
# context shares the pairs it inherited without copying them.
_Stack: TypeAlias = "tuple[_Entry, _Stack] | None"

# One variable for every Measure: a context keeps each variable ever set in it for as long
# as it lives, so a variable per Measure would grow a long-lived thread without bound.
# A context sees only its own entries, and those of the context it was copied from.
_RUNNING: ContextVar[_Stack] = ContextVar("running", default=None)


def _owner() -> tuple[threading.Thread, object]:
    # A copied context (an asyncio task, to_thread, a thread on free-threaded 3.14) still
    # sees the entries of its parent, so the owner is checked as well as the context.
    asyncio = sys.modules.get("asyncio")
    task = None
    if asyncio is not None:
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
    return threading.current_thread(), task


def checked(timing: Timing, name: str, desc: str | None) -> None:
    """Raise as ``build`` would for a name or description that cannot be sent."""
    if not isinstance(timing, Timing):
        raise TypeError(f"timing must be a Timing, got {shown(timing)}")
    render(Metric(name=name, dur=0.0, desc=desc))


class Measure:
    """What ``Timing.measure`` returns: a context manager and a function decorator.

    As a context manager it times the block; it may be entered again, even from several
    threads or asyncio tasks at once, and each entry records its own metric. As a
    decorator it times every call of a plain function, or every run of an ``async``
    function up to its return. A generator function raises ``TypeError``, because calling
    one only creates the generator. A block must be left once, in the thread or task that
    entered it: leaving it in another one, even one that copied the context, or leaving it
    a second time from a copy of the context raises ``RuntimeError`` and records nothing.
    Usually created by ``Timing.measure``; the constructor checks its arguments the same way.

    >>> import asyncio, itertools
    >>> from timingheader import Timing
    >>> ticks = itertools.count(0.0, 0.01)
    >>> timing = Timing(clock=lambda: next(ticks))
    >>> @timing.measure("fetch")
    ... async def fetch() -> int:
    ...     await asyncio.sleep(0)
    ...     return 200
    >>> asyncio.run(fetch()), timing.header()
    (200, 'fetch;dur=10')
    """

    def __init__(self, timing: Timing, name: str, desc: str | None) -> None:
        checked(timing, name, desc)
        self._timing = timing
        self._name = name
        self._desc = desc

    def __enter__(self) -> None:
        # The start times live in the context, so one Measure entered from several threads
        # or asyncio tasks at once keeps each entry apart.
        _RUNNING.set((_Entry(self, self._timing._clock()), _RUNNING.get()))

    def __exit__(self, *exc_info: object) -> None:
        above: list[_Entry] = []
        node = _RUNNING.get()
        while node is not None:
            entry, node = node
            if entry.measure is not self:
                above.append(entry)
                continue
            thread, task = _owner()
            if entry.owner[0] is not thread or entry.owner[1] is not task:
                raise RuntimeError("measure exited in another thread or task than its enter")
            # Only the entries above this one are rebuilt: none for an innermost exit.
            for kept in reversed(above):
                node = (kept, node)
            _RUNNING.set(node)
            if entry.left:
                raise RuntimeError("measure entry already exited in a copy of this context")
            # Only the owning thread gets here, so no other thread can race this flag.
            entry.left = True
            self._timing._finish(self._name, self._desc, entry.start)
            return
        raise RuntimeError("measure exited without a matching enter in this context")

    def __call__(self, func: F) -> F:
        if not callable(func):
            raise TypeError(f"measure decorates a function, got {shown(func)}")
        if inspect.isgeneratorfunction(func) or inspect.isasyncgenfunction(func):
            raise TypeError("measure cannot time a generator function; time a block inside it")
        timing, name, desc = self._timing, self._name, self._desc
        if inspect.iscoroutinefunction(func):
            # Timing the call alone would only time creating the coroutine, not running it.
            @functools.wraps(func)
            async def run_async(*args: Any, **kwargs: Any) -> Any:
                start = timing._clock()
                try:
                    return await func(*args, **kwargs)
                finally:
                    timing._finish(name, desc, start)

            return cast(F, run_async)

        @functools.wraps(func)
        def run(*args: Any, **kwargs: Any) -> Any:
            start = timing._clock()
            try:
                return func(*args, **kwargs)
            finally:
                timing._finish(name, desc, start)

        return cast(F, run)

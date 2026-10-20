"""The single metric value carried by a Server-Timing header."""

from __future__ import annotations

import math
from dataclasses import dataclass

from ._errors import shown
from ._syntax import ascii_lower


@dataclass(frozen=True, init=False)
class Metric:
    """One Server-Timing metric: a name, an optional duration, label and extra parameters.

    ``dur`` is ``None`` when the header gave no usable duration and ``desc`` is ``None``
    when it gave no description. ``params`` holds any other parameters in header order as
    ``(name, value)`` pairs; names are compared without regard to ASCII case and stored
    with A to Z in lower case, and a list is stored as a tuple. An ``int`` duration, a
    subclass such as an ``IntEnum`` included, is stored as the ``float`` of its exact
    value, one beyond the range of a float as an infinity; a ``bool`` is kept. Durations are
    milliseconds by convention. Nothing is validated here, because ``parse`` keeps what a
    browser keeps; ``build`` and ``str()`` check every part before writing it.

    >>> from timingheader import Metric
    >>> metric = Metric("cdn", 7, params=[("Hit", "1")])
    >>> metric
    Metric(name='cdn', dur=7.0, desc=None, params=(('hit', '1'),))
    >>> metric == Metric("cdn", dur=7.0, params=(("hit", "1"),))
    True
    """

    name: str
    dur: float | None = None
    desc: str | None = None
    params: tuple[tuple[str, str], ...] = ()

    def __init__(
        self,
        name: str,
        dur: float | None = None,
        desc: str | None = None,
        params: tuple[tuple[str, str], ...] | list[tuple[str, str]] = (),
    ) -> None:
        # Parameter names are case-insensitive and durations are floats: normalising both
        # makes a metric equal to what parse reads back from its serialization. Values of
        # the wrong type are left alone for build to reject with a clear message.
        if isinstance(dur, int) and not isinstance(dur, bool):
            # The exact int value, so a subclass (an IntEnum, HTTPStatus) cannot steer the
            # conversion through its own hooks.
            exact = int.__index__(dur)
            try:
                dur = float(exact)
            except OverflowError:
                dur = math.inf if exact > 0 else -math.inf
        if isinstance(params, list):
            params = tuple(params)
        if isinstance(params, tuple) and all(_is_pair(pair) for pair in params):
            params = tuple((ascii_lower(key), value) for key, value in params)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "dur", dur)
        object.__setattr__(self, "desc", desc)
        object.__setattr__(self, "params", params)

    @property
    def duration(self) -> float:
        """The duration a browser exposes: ``dur``, or ``0.0`` when there is none.

        >>> from timingheader import Metric
        >>> Metric("db", dur=53.0).duration, Metric("miss").duration
        (53.0, 0.0)
        """
        return 0.0 if self.dur is None else self.dur

    @property
    def description(self) -> str:
        """The description a browser exposes: ``desc``, or ``""`` when there is none.

        >>> from timingheader import Metric
        >>> Metric("db", desc="primary").description, Metric("miss").description
        ('primary', '')
        """
        return "" if self.desc is None else self.desc

    def param(self, name: str) -> str | None:
        """The value of the extra parameter ``name`` (case-insensitive), if present.

        Raises ``TypeError`` when ``name`` is not a ``str``, or when ``params`` does not
        hold ``(name, value)`` pairs with a ``str`` name.

        >>> from timingheader import parse
        >>> (metric,) = parse("cdn;HIT=1;region=eu")
        >>> metric.param("hit"), metric.param("Region"), metric.param("miss")
        ('1', 'eu', None)
        """
        if not isinstance(name, str):
            raise TypeError(f"a parameter name must be a str, got {shown(name)}")
        wanted = ascii_lower(name)
        params = self.params
        if not isinstance(params, tuple):
            raise TypeError(f"params must hold (name, value) pairs, got {shown(params)}")
        for pair in params:
            if not _is_pair(pair):
                raise TypeError(f"params must hold (name, value) pairs, got {shown(pair)}")
            if ascii_lower(pair[0]) == wanted:
                return pair[1]
        return None

    def __str__(self) -> str:
        """Serialize this metric alone, as ``build`` would, raising as ``build`` does.

        >>> from timingheader import Metric
        >>> str(Metric("cache", 0.75, "Cache Read"))
        'cache;dur=0.75;desc="Cache Read"'
        """
        from ._build import render

        return render(self)


def _is_pair(pair: object) -> bool:
    return isinstance(pair, tuple) and len(pair) == 2 and isinstance(pair[0], str)

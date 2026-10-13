"""The single metric value carried by a Server-Timing header."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    """One Server-Timing metric: a name, an optional duration, label and extra parameters.

    ``dur`` is ``None`` when the header gave no usable duration and ``desc`` is ``None``
    when it gave no description. ``params`` holds any other parameters in header order as
    ``(name, value)`` pairs; names are case-insensitive and stored in lower case. An ``int``
    duration is stored as a ``float``. Durations are milliseconds by convention.
    """

    name: str
    dur: float | None = None
    desc: str | None = None
    params: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        # Parameter names are case-insensitive and durations are floats: normalising both
        # makes a metric equal to what parse reads back from its serialization. Values of
        # the wrong type are left alone for build to reject with a clear message.
        if type(self.dur) is int:
            with contextlib.suppress(OverflowError):
                object.__setattr__(self, "dur", float(self.dur))
        pairs = self.params
        if isinstance(pairs, tuple) and all(
            isinstance(pair, tuple) and len(pair) == 2 and isinstance(pair[0], str)
            for pair in pairs
        ):
            object.__setattr__(self, "params", tuple((key.lower(), value) for key, value in pairs))

    @property
    def duration(self) -> float:
        """The duration a browser exposes: ``dur``, or ``0.0`` when there is none."""
        return 0.0 if self.dur is None else self.dur

    @property
    def description(self) -> str:
        """The description a browser exposes: ``desc``, or ``""`` when there is none."""
        return "" if self.desc is None else self.desc

    def param(self, name: str) -> str | None:
        """The value of the extra parameter ``name`` (case-insensitive), if present."""
        wanted = name.lower()
        for key, value in self.params:
            if key.lower() == wanted:
                return value
        return None

    def __str__(self) -> str:
        """Serialize this metric alone, as ``build`` would."""
        from ._build import render

        return render(self)

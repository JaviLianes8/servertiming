"""The single metric value carried by a Server-Timing header."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    """One Server-Timing metric: a name, an optional duration, label and extra parameters.

    ``dur`` is ``None`` when the header gave no usable duration and ``desc`` is ``None``
    when it gave no description. ``params`` holds any other parameters in header order as
    ``(name, value)`` pairs with lower-case names. Durations are milliseconds by convention.
    """

    name: str
    dur: float | None = None
    desc: str | None = None
    params: tuple[tuple[str, str], ...] = ()

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

"""The single metric value carried by a Server-Timing header."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Metric:
    """One Server-Timing metric: a name, an optional duration and an optional label.

    Durations follow the header convention and are expressed in milliseconds.
    """

    name: str
    dur: float | None = None
    desc: str | None = None

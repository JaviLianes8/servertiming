"""Build and parse the HTTP Server-Timing header, with a tiny collector for durations."""

from __future__ import annotations

from ._build import build
from ._collector import Timing
from ._metric import Metric
from ._parse import parse

__version__ = "0.1.0"

__all__ = ["Metric", "Timing", "build", "parse"]

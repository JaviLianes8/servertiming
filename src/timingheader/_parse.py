"""Read Server-Timing field values the way browsers do, never raising on bad input."""

from __future__ import annotations

from collections.abc import Iterable

from ._metric import Metric
from ._number import parse_number
from ._syntax import OWS, TCHARS


def field_list(value: str | Iterable[str]) -> list[str]:
    """One field value or several (headers, then trailers) as a checked list."""
    if isinstance(value, (bytes, bytearray)):
        raise TypeError("field values must be str; decode header bytes as latin-1 first")
    fields = [value] if isinstance(value, str) else list(value)
    for field in fields:
        if not isinstance(field, str):
            raise TypeError(f"field values must be str, got {field!r}")
    return fields


def parse_lenient(fields: list[str]) -> list[Metric]:
    """Tokenize the field values, skipping what the spec says to ignore.

    Repeated fields are joined with ``", "`` first, as Fetch does before parsing.
    """
    reader = _Reader(", ".join(fields))
    metrics: list[Metric] = []
    while not reader.done():
        reader.skip_ows()
        name = reader.token()
        if not name:
            reader.skip_to(",")
            reader.advance()
            continue
        params: dict[str, str] = {}
        while True:
            # Extraneous characters after a name or a value are ignored (spec section 2).
            reader.skip_to(",;")
            if reader.peek() != ";":
                break
            reader.advance()
            reader.skip_ows()
            key = reader.token().lower()
            reader.skip_ows()
            value = ""
            if reader.peek() == "=":
                reader.advance()
                reader.skip_ows()
                value = reader.quoted() if reader.peek() == '"' else reader.token()
            # The first occurrence wins, even when it is empty or invalid.
            if key and key not in params:
                params[key] = value
        reader.advance()
        metrics.append(metric_from_params(name, params))
    return metrics


def metric_from_params(name: str, params: dict[str, str]) -> Metric:
    raw_dur = params.pop("dur", None)
    desc = params.pop("desc", None)
    dur = None if raw_dur is None else parse_number(raw_dur)
    return Metric(name, dur, desc, tuple(params.items()))


class _Reader:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def done(self) -> bool:
        return self.pos >= len(self.text)

    def peek(self) -> str:
        return self.text[self.pos : self.pos + 1]

    def advance(self) -> None:
        self.pos += 1

    def skip_ows(self) -> None:
        while self.peek() and self.peek() in OWS:
            self.pos += 1

    def token(self) -> str:
        start = self.pos
        while self.peek() and self.peek() in TCHARS:
            self.pos += 1
        return self.text[start : self.pos]

    def skip_to(self, stops: str) -> None:
        while self.peek() and self.peek() not in stops:
            if self.peek() == '"':
                self.quoted()
            else:
                self.pos += 1

    def quoted(self) -> str:
        """Read a quoted string; one that never closes reads as empty, as WPT expects."""
        self.pos += 1
        chars: list[str] = []
        while not self.done():
            char = self.text[self.pos]
            self.pos += 1
            if char == '"':
                return "".join(chars)
            if char == "\\":
                if self.done():
                    break
                char = self.text[self.pos]
                self.pos += 1
            chars.append(char)
        return ""

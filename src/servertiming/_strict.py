"""Validate Server-Timing field values against the ABNF, raising at the first error."""

from __future__ import annotations

from ._errors import ServerTimingError
from ._metric import Metric
from ._number import is_valid_number
from ._parse import metric_from_params
from ._syntax import OWS, TCHARS, is_quotable


def parse_strict(text: str, field: int) -> list[Metric]:
    """Parse one field value that must match ``#server-timing-metric`` exactly.

    Empty list elements are accepted, as RFC 9110 5.6.1.2 requires of recipients. A
    repeated parameter name (which the spec says senders should not produce) and a ``dur``
    that is not an HTML valid floating-point number are errors too.
    """
    return _Strict(text, field).metrics()


class _Strict:
    def __init__(self, text: str, field: int) -> None:
        self.text = text
        self.field = field
        self.pos = 0

    def fail(self, message: str, position: int | None = None) -> ServerTimingError:
        where = self.pos if position is None else position
        found = repr(self.text[where]) if where < len(self.text) else "the end"
        return ServerTimingError(
            f"{message} at position {where} (found {found})", where, self.field
        )

    def peek(self) -> str:
        return self.text[self.pos : self.pos + 1]

    def skip_ows(self) -> None:
        while self.peek() and self.peek() in OWS:
            self.pos += 1

    def token(self, what: str) -> str:
        start = self.pos
        while self.peek() and self.peek() in TCHARS:
            self.pos += 1
        if self.pos == start:
            raise self.fail(f"expected {what}")
        return self.text[start : self.pos]

    def metrics(self) -> list[Metric]:
        found: list[Metric] = []
        while True:
            self.skip_ows()
            if not self.peek():
                return found
            if self.peek() != ",":
                found.append(self.metric())
                self.skip_ows()
                if not self.peek():
                    return found
                if self.peek() != ",":
                    raise self.fail("expected ',' or ';'")
            self.pos += 1

    def metric(self) -> Metric:
        name = self.token("a metric name (a token)")
        params: dict[str, str] = {}
        while True:
            mark = self.pos
            self.skip_ows()
            if self.peek() != ";":
                self.pos = mark
                return metric_from_params(name, params)
            self.pos += 1
            self.skip_ows()
            key_at = self.pos
            key = self.token("a parameter name (a token)").lower()
            self.skip_ows()
            if self.peek() != "=":
                raise self.fail("expected '=' after the parameter name")
            self.pos += 1
            self.skip_ows()
            value_at = self.pos
            value = self.quoted() if self.peek() == '"' else self.token("a token or quoted string")
            if key in params:
                raise self.fail(f"parameter {key!r} is repeated", key_at)
            if key == "dur" and not is_valid_number(value):
                raise self.fail("dur is not a valid floating-point number", value_at)
            params[key] = value

    def quoted(self) -> str:
        start = self.pos
        self.pos += 1
        chars: list[str] = []
        while self.peek():
            char = self.peek()
            if char == '"':
                self.pos += 1
                return "".join(chars)
            if char == "\\":
                self.pos += 1
                char = self.peek()
                if not char:
                    break
            # qdtext and quoted-pair admit the same characters once quote and backslash are out.
            if not is_quotable(char):
                raise self.fail("character not allowed in a quoted string")
            chars.append(char)
            self.pos += 1
        raise self.fail("unterminated quoted string", start)

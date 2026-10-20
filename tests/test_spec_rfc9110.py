"""Tokens, quoted strings, whitespace and lists against RFC 9110, read from the fetched text.

The ABNF rules are parsed out of the fetched RFC 9110 (URL and sha256 in
tests/upstream/MANIFEST.json, fetched 2026-10-20), never retyped, and compared with the
strict parser and the builder code point by code point. The file is not committed; these
tests skip until `python scripts/fetch_upstream.py` has run.
"""

from __future__ import annotations

import re

import pytest
from conftest import upstream_document

from timingheader import Metric, ServerTimingError, build, parse

SAMPLE = [chr(code) for code in range(0x300)] + ["\ud800", "\U0001f600"]
# RFC 5234 core rules that RFC 9110 uses by name (hand-written from RFC 5234 appendix B.1).
CORE = {
    "HTAB": "\t",
    "SP": " ",
    "DIGIT": "0123456789",
    "ALPHA": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "VCHAR": "".join(map(chr, range(0x21, 0x7F))),
}


@pytest.fixture(scope="module")
def rfc() -> str:
    return upstream_document("rfc9110.txt")


def rule(text: str, name: str) -> str:
    """The right-hand side of one ABNF rule of the fetched text, comments removed."""
    stop = r"(?=\n\s*\n|\n *[\w-]+ +=)"
    match = re.search(rf"^ *{re.escape(name)} +=(.*?){stop}", text, re.M | re.S)
    assert match is not None, name
    return re.sub(r";[^\n]*", "", match.group(1))


def chars(text: str, body: str) -> set[str]:
    """Expand an alternation of quoted chars, %x values, ranges and named rules."""
    found: set[str] = set()
    for alt in re.findall(r'"[^"]"|%x[0-9A-F]+(?:-[0-9A-F]+)?|[A-Za-z][\w-]*', body):
        if alt.startswith('"'):
            found.add(alt[1])
        elif alt.startswith("%x"):
            low, _, high = alt[2:].partition("-")
            found.update(map(chr, range(int(low, 16), int(high or low, 16) + 1)))
        else:
            found.update(CORE[alt] if alt in CORE else chars(text, rule(text, alt)))
    return found


def _strict_ok(text: str) -> bool:
    try:
        parse(text, strict=True)
    except ServerTimingError:
        return False
    return True


def _builds(metric: Metric) -> bool:
    try:
        build([metric])
    except ServerTimingError:
        return False
    return True


def test_names_are_exactly_tokens(rfc: str) -> None:
    tchar = chars(rfc, rule(rfc, "tchar"))
    assert len(tchar) == 77
    for char in SAMPLE:
        assert _strict_ok(f"a{char}") == (char in tchar or char in " \t"), repr(char)
        assert _strict_ok(f"{char}a;{char}={char}") == (char in tchar), repr(char)
        assert _builds(Metric(char)) == (char in tchar), repr(char)
        assert _builds(Metric("a", params=((f"x{char}", "1"),))) == (char in tchar), repr(char)
        assert (parse(f"{char}x")[:1] == [Metric(f"{char}x")]) == (char in tchar), repr(char)


def test_quoted_strings_are_exactly_qdtext_and_quoted_pair(rfc: str) -> None:
    qdtext = chars(rfc, rule(rfc, "qdtext"))
    escaped = chars(rfc, rule(rfc, "quoted-pair"))
    assert len(qdtext) == 2 + 1 + 57 + 34 + 128
    assert escaped == qdtext | {'"', "\\"}
    for char in SAMPLE:
        assert _strict_ok(f'a;desc="{char}"') == (char in qdtext), repr(char)
        assert _strict_ok(f'a;desc="\\{char}"') == (char in escaped), repr(char)
        assert _builds(Metric("a", desc=char)) == (char in escaped), repr(char)
        assert _builds(Metric("a", params=(("x", char),))) == (char in escaped), repr(char)


def test_the_builder_writes_tokens_bare_and_the_rest_quoted(rfc: str) -> None:
    tchar = chars(rfc, rule(rfc, "tchar"))
    for char in SAMPLE:
        if _builds(Metric("a", desc=char)):
            written = build([Metric("a", desc=char)])
            escape = "\\" if char in '"\\' else ""
            expected = f"a;desc={char}" if char in tchar else f'a;desc="{escape}{char}"'
            assert written == expected, repr(char)
            assert parse(written, strict=True) == [Metric("a", desc=char)]


def test_optional_whitespace_is_space_and_tab_only(rfc: str) -> None:
    ows = chars(rfc, rule(rfc, "OWS"))
    assert ows == {" ", "\t"}
    allowed = ows | chars(rfc, rule(rfc, "tchar"))
    for char in SAMPLE:
        assert _strict_ok(f"a{char};dur=1") == (char in allowed), repr(char)
        assert _strict_ok(f"a;{char}dur=1") == (char in allowed), repr(char)
        assert _strict_ok(f"a;dur{char}=1") == (char in allowed), repr(char)
        assert _strict_ok(f"a;x={char}1") == (char in allowed), repr(char)
        assert _strict_ok(f"a;x=1{char}") == (char in allowed), repr(char)
        assert _strict_ok(f"a{char},b") == (char in allowed), repr(char)


def test_the_list_rule_for_senders_and_recipients(rfc: str) -> None:
    text = re.sub(r"\s+", " ", rfc)
    assert "a sender MUST NOT generate empty list elements" in text
    assert "A recipient MUST parse and ignore a reasonable number of empty list" in text
    for value in ("a,,b", ", a", "a ,", "a, ,b"):
        assert [m.name for m in parse(value)] == [n for n in ("a", "b") if n in value]
        with pytest.raises(ServerTimingError, match="empty list element"):
            parse(value, strict=True)
    assert parse("", strict=True) == [] and parse("  ", strict=True) == []

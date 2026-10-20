"""The W3C Server Timing grammar, rules and example, read from the fetched source.

Source: the Bikeshed source of the Editor's Draft at a fixed commit, and the WHATWG Fetch
Standard at a fixed commit snapshot (URLs and sha256 in tests/upstream/MANIFEST.json,
fetched 2026-10-20). Nothing here is retyped from the documents: the rules, the example
headers and the table of the metrics they carry are cut from the fetched text. The files
are not committed; these tests skip until `python scripts/fetch_upstream.py` has run.
"""

from __future__ import annotations

import html
import re

import pytest
from conftest import prose, upstream_document

from timingheader import Metric, ServerTimingError, parse


@pytest.fixture(scope="module")
def spec() -> str:
    return upstream_document("server-timing.bs")


def _grammar(spec: str) -> dict[str, str]:
    block = spec.split("header field=] is as follows:</p>", 1)[1].split("</pre>", 1)[0]
    pairs = re.findall(r"^\s*([\w-]+)\s*=\s*(.+?)\s*$", html.unescape(block), re.M)
    return dict(pairs)


def test_the_grammar_is_the_one_strict_mode_implements(spec: str) -> None:
    assert _grammar(spec) == {
        "Server-Timing": "#server-timing-metric",
        "server-timing-metric": 'metric-name *( OWS ";" OWS server-timing-param )',
        "metric-name": "token",
        "server-timing-param": 'server-timing-param-name OWS "=" OWS server-timing-param-value',
        "server-timing-param-name": "token",
        "server-timing-param-value": "token / quoted-string",
    }


def test_whitespace_where_the_grammar_allows_it(spec: str) -> None:
    assert 'OWS ";" OWS' in _grammar(spec)["server-timing-metric"]
    assert parse('db \t; \tdur \t= \t5 ;desc = "x"', strict=True) == [Metric("db", 5.0, "x")]
    with pytest.raises(ServerTimingError):
        parse("db;dur", strict=True)


def _example(spec: str) -> tuple[list[str], list[tuple[str, float | None, str | None]]]:
    section = spec.split('id="example-server-timing-headers"', 1)[1]
    lines = html.unescape(section.split("</pre>", 1)[0]).splitlines()
    fields = [line.split(":", 1)[1].strip() for line in lines if "Server-Timing:" in line]
    body = section.split("<tbody>", 1)[1].split("</tbody>", 1)[0]
    rows = re.findall(r"<tr><td>(.*?)</td><td>(.*?)</td><td>(.*?)</td></tr>", body)
    table = [(name, float(dur) if dur else None, desc or None) for name, dur, desc in rows]
    return fields, table


def test_the_example_headers_and_trailer_carry_the_metrics_of_its_table(spec: str) -> None:
    fields, table = _example(spec)
    assert len(fields) == 4 and len(table) == 7
    assert "Trailer: Server-Timing" in spec
    got = [(m.name, m.dur, m.desc) for m in parse(fields)]
    assert got == table
    assert [(m.name, m.dur, m.desc) for m in parse(fields, strict=True)] == table


def test_repeated_names_are_all_kept(spec: str) -> None:
    rule = prose(spec)
    assert "MUST process and expose all such entries" in rule
    assert [m.dur for m in parse("db;dur=1, db;dur=2, db")] == [1.0, 2.0, None]


def test_only_the_first_instance_of_a_parameter_counts(spec: str) -> None:
    rule = prose(spec)
    assert "only the first instance is to be considered, even if the" in rule
    assert "is incomplete or invalid" in rule
    assert parse("a;dur=1;dur=2;DUR=3")[0].dur == 1.0
    assert parse("a;dur=x;dur=2")[0].dur is None
    assert parse("a;desc;desc=late")[0].desc == ""
    with pytest.raises(ServerTimingError, match="repeated"):
        parse("a;dur=1;Dur=2", strict=True)


def test_unknown_parameters_are_ignored_by_the_browser_view(spec: str) -> None:
    assert "MUST ignore those tokens and continue processing" in prose(spec)
    (metric,) = parse("cdn;hit=1;dur=5;pop=MAD")
    assert (metric.name, metric.duration, metric.description) == ("cdn", 5.0, "")
    assert metric.params == (("hit", "1"), ("pop", "MAD"))


def test_extraneous_characters_are_ignored(spec: str) -> None:
    rule = prose(spec)
    assert "MUST ignore extraneous characters found after a server-timing-param-value" in rule
    assert "MUST ignore extraneous characters found after a metric-name" in rule
    assert parse('db junk;dur=1 2 3;desc="a" tail') == [Metric("db", 1.0, "a")]


def test_the_getters_default_to_zero_and_empty(spec: str) -> None:
    rule = prose(spec)
    assert '[ "dur" ] does not [=map/exists|exist=], return 0' in rule
    assert "If |dur| is an error, return 0" in rule
    assert '[ "desc" ] if it [=map/exists=], otherwise the empty string' in rule
    bare, bad = parse("a, b;dur=x")
    assert (bare.duration, bare.description, bad.duration) == (0.0, "", 0.0)


def test_repeated_fields_are_joined_with_comma_space_as_fetch_does() -> None:
    fetch = prose(upstream_document("whatwg-fetch.html"))
    assert "whose name is a byte-case-insensitive match for name , separated from each" in fetch
    assert "other by 0x2C 0x20, in order" in fetch
    assert parse(["a;desc=x", "b"]) == parse("a;desc=x, b")
    # A quoted string left open in one field does not swallow the next one's metrics only
    # because the browser reads the joined value; the joined reading is what is promised.
    assert parse(['a;desc="open', "b"]) == parse('a;desc="open, b')

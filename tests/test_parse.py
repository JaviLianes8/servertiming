"""Lenient parsing. Cases are written by hand from the spec prose (section 2) and agree
with the WPT corpus, which runs separately when fetched."""

from __future__ import annotations

import pytest

from timingheader import Metric, build, parse


def test_parse_a_single_bare_metric() -> None:
    assert parse("cache") == [Metric("cache")]


def test_parse_duration_and_description() -> None:
    assert parse('db;dur=12.3;desc="Database"') == [Metric("db", dur=12.3, desc="Database")]


def test_parse_multiple_metrics() -> None:
    assert parse("app;dur=5, db;dur=2") == [Metric("app", dur=5.0), Metric("db", dur=2.0)]


def test_parse_handles_separators_inside_a_quoted_description() -> None:
    assert parse('db;desc="one, two; =";dur=1') == [Metric("db", dur=1.0, desc="one, two; =")]


def test_parse_unescapes_quoted_pairs() -> None:
    assert parse('db;desc="a \\"quote\\" and \\\\"') == [Metric("db", desc='a "quote" and \\')]


def test_a_description_is_absent_or_empty() -> None:
    assert parse("db") == [Metric("db")]
    assert parse("db;desc=") == [Metric("db", desc="")]


def test_an_unreadable_duration_is_none_and_reads_as_zero() -> None:
    (metric,) = parse("db;dur=fast")
    assert metric.dur is None
    assert metric.duration == 0.0


def test_a_duration_may_be_quoted() -> None:
    assert parse('db;dur="7.5"') == [Metric("db", dur=7.5)]


def test_a_duration_uses_the_html_number_rules() -> None:
    assert parse("db;dur=12ms")[0].dur == 12.0
    assert parse("db;dur=inf")[0].dur is None


def test_parameter_names_are_case_insensitive() -> None:
    assert parse("db;DUR=3;Desc=x;Hit=1") == [Metric("db", 3.0, "x", (("hit", "1"),))]


def test_the_first_occurrence_of_a_parameter_wins() -> None:
    assert parse("db;dur=1;dur=2;desc=a;desc=b") == [Metric("db", dur=1.0, desc="a")]


def test_the_first_occurrence_wins_even_when_invalid() -> None:
    assert parse("db;dur=x;dur=2") == [Metric("db", dur=None)]
    assert parse("db;desc;desc=late") == [Metric("db", desc="")]


def test_extension_parameters_are_kept_in_order() -> None:
    (metric,) = parse('cdn;region="eu west";hit;dur=4')
    assert metric.params == (("region", "eu west"), ("hit", ""))
    assert metric.param("REGION") == "eu west"
    assert metric.param("missing") is None


def test_extraneous_characters_after_a_value_are_ignored() -> None:
    assert parse("db;desc=d1 d2;dur=5") == [Metric("db", dur=5.0, desc="d1")]
    assert parse('db;desc="d1" d2, x') == [Metric("db", desc="d1"), Metric("x")]


def test_extraneous_characters_after_a_name_are_ignored() -> None:
    assert parse('db==  "a,b"junk;dur=1, x') == [Metric("db", dur=1.0), Metric("x")]


def test_whitespace_around_separators_is_skipped() -> None:
    assert parse("db \t; dur = 1 ;\tdesc = x , y") == [Metric("db", 1.0, "x"), Metric("y")]


def test_an_entry_without_a_token_name_is_dropped() -> None:
    assert parse("[x];dur=1, =, ;, ok") == [Metric("ok")]


def test_an_unterminated_quoted_string_reads_as_empty() -> None:
    assert parse('db;desc="never closed, x') == [Metric("db", desc="")]
    assert parse('db;desc="a\\') == [Metric("db", desc="")]


def test_names_keep_their_case_and_repeat() -> None:
    assert parse("Db;dur=1, Db;dur=2") == [Metric("Db", dur=1.0), Metric("Db", dur=2.0)]


def test_several_fields_are_read_in_order() -> None:
    fields = ["miss, db;dur=53", "total;dur=123.4"]
    assert [m.name for m in parse(fields)] == ["miss", "db", "total"]


def test_fields_are_joined_like_fetch_does() -> None:
    # Fetch joins repeated fields with ", " before parsing, so an open quote runs on.
    assert parse(['a;desc="x', 'y", b']) == [Metric("a", desc="x, y"), Metric("b")]


def test_parse_of_nothing_is_empty() -> None:
    assert parse("") == []
    assert parse([]) == []
    assert parse(" , ,\t") == []


def test_parse_rejects_a_non_str_field() -> None:
    with pytest.raises(TypeError):
        parse([b"db"])  # type: ignore[list-item]
    with pytest.raises(TypeError):
        parse(b"db")  # type: ignore[arg-type]


def test_round_trip_through_build_and_parse() -> None:
    metrics = [
        Metric("app", dur=5.0, desc="application"),
        Metric("db", dur=2.5, desc='a, tricky "one"'),
        Metric("cdn", params=(("hit", "1"), ("pop", "MAD 2"))),
        Metric("cache"),
    ]
    assert parse(build(metrics)) == metrics
    assert parse(build(metrics), strict=True) == metrics

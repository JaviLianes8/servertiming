from servertiming import Metric, build, parse


def test_parse_a_single_bare_metric() -> None:
    assert parse("cache") == [Metric("cache")]


def test_parse_duration_and_description() -> None:
    assert parse('db;dur=12.3;desc="Database"') == [Metric("db", dur=12.3, desc="Database")]


def test_parse_multiple_metrics() -> None:
    assert parse("app;dur=5, db;dur=2") == [Metric("app", dur=5.0), Metric("db", dur=2.0)]


def test_parse_handles_a_comma_inside_a_quoted_description() -> None:
    assert parse('db;desc="one, two"') == [Metric("db", desc="one, two")]


def test_parse_unescapes_quotes_in_a_description() -> None:
    assert parse('db;desc="a \\"quote\\""') == [Metric("db", desc='a "quote"')]


def test_parse_tolerates_a_missing_duration() -> None:
    assert parse("db;desc=work") == [Metric("db", desc="work")]


def test_parse_turns_an_unreadable_duration_into_none() -> None:
    assert parse("db;dur=fast") == [Metric("db", dur=None)]


def test_parse_ignores_unknown_parameters() -> None:
    assert parse("db;dur=2;extra=1") == [Metric("db", dur=2.0)]


def test_parse_skips_empty_entries() -> None:
    assert parse("app;dur=1,,db;dur=2") == [Metric("app", dur=1.0), Metric("db", dur=2.0)]


def test_parse_of_an_empty_header_is_empty() -> None:
    assert parse("") == []


def test_parse_drops_a_non_finite_duration() -> None:
    assert parse("db;dur=inf") == [Metric("db", dur=None)]


def test_round_trip_through_build_and_parse() -> None:
    metrics = [
        Metric("app", dur=5.0, desc="application"),
        Metric("db", dur=2.5, desc='a, tricky "one"'),
        Metric("cache"),
    ]
    assert parse(build(metrics)) == metrics

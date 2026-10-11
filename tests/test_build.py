import pytest

from servertiming import Metric, build


def test_build_a_single_bare_metric() -> None:
    assert build([Metric("cache")]) == "cache"


def test_build_a_metric_with_duration() -> None:
    assert build([Metric("db", dur=12.3)]) == "db;dur=12.3"


def test_build_a_metric_with_duration_and_description() -> None:
    assert (
        build([Metric("db", dur=12.3, desc="Database read")]) == 'db;dur=12.3;desc="Database read"'
    )


def test_build_joins_multiple_metrics_with_commas() -> None:
    header = build([Metric("app", dur=5.0), Metric("db", dur=2.0)])
    assert header == "app;dur=5, db;dur=2"


def test_duration_drops_a_trailing_zero_decimal() -> None:
    assert build([Metric("cpu", dur=100.0)]) == "cpu;dur=100"


def test_duration_keeps_a_fractional_value() -> None:
    assert build([Metric("cpu", dur=0.5)]) == "cpu;dur=0.5"


def test_description_without_quoting_when_it_is_a_token() -> None:
    assert build([Metric("cpu", desc="work")]) == "cpu;desc=work"


def test_description_is_quoted_when_it_contains_spaces() -> None:
    assert build([Metric("cpu", desc="total work")]) == 'cpu;desc="total work"'


def test_description_quotes_are_escaped() -> None:
    assert build([Metric("cpu", desc='a "quote"')]) == 'cpu;desc="a \\"quote\\""'


def test_empty_description_is_quoted() -> None:
    assert build([Metric("cpu", desc="")]) == 'cpu;desc=""'


def test_build_rejects_an_invalid_name() -> None:
    with pytest.raises(ValueError):
        build([Metric("bad name")])


def test_build_rejects_a_non_finite_duration() -> None:
    with pytest.raises(ValueError):
        build([Metric("cpu", dur=float("inf"))])

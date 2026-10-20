from __future__ import annotations

import pytest

from timingheader import Metric, ServerTimingError, build


def test_build_a_single_bare_metric() -> None:
    assert build([Metric("cache")]) == "cache"


def test_build_a_metric_with_duration_and_description() -> None:
    assert build([Metric("db", 12.3, "Database read")]) == 'db;dur=12.3;desc="Database read"'


def test_build_joins_multiple_metrics_with_commas() -> None:
    assert build([Metric("app", dur=5.0), Metric("db", dur=2.0)]) == "app;dur=5, db;dur=2"


def test_build_of_nothing_is_empty() -> None:
    assert build([]) == ""


@pytest.mark.parametrize(
    ("dur", "text"),
    [(100.0, "100"), (0.5, "0.5"), (7, "7"), (-0.0, "0"), (1e-05, "1e-5"), (1e16, "1e16")],
)
def test_durations_are_written_compactly(dur: float, text: str) -> None:
    assert build([Metric("cpu", dur=dur)]) == f"cpu;dur={text}"


@pytest.mark.parametrize(
    ("precision", "text"), [(0, "13"), (1, "12.6"), (2, "12.57"), (3, "12.568"), (6, "12.5678")]
)
def test_precision_rounds_durations(precision: int, text: str) -> None:
    assert build([Metric("cpu", dur=12.5678)], precision=precision) == f"cpu;dur={text}"


def test_precision_never_writes_a_negative_zero() -> None:
    assert build([Metric("cpu", dur=-0.0001)], precision=2) == "cpu;dur=0"


@pytest.mark.parametrize("precision", [-1, 21, 10**20])
def test_build_rejects_a_precision_out_of_range(precision: int) -> None:
    with pytest.raises(ServerTimingError, match="from 0 to 20"):
        build([Metric("cpu", dur=1.0)], precision=precision)


@pytest.mark.parametrize("precision", [1.5, True, "2"])
def test_build_rejects_a_precision_that_is_not_an_int(precision: object) -> None:
    with pytest.raises(TypeError, match="precision must be an int"):
        build([Metric("cpu", dur=1.0)], precision=precision)  # type: ignore[arg-type]


def test_the_largest_precision_is_accepted() -> None:
    assert build([Metric("cpu", dur=0.1)], precision=20) == "cpu;dur=0.10000000000000000555"


def test_description_without_quoting_when_it_is_a_token() -> None:
    assert build([Metric("cpu", desc="work")]) == "cpu;desc=work"


def test_description_quotes_and_backslashes_are_escaped() -> None:
    assert build([Metric("cpu", desc='a "b" \\ c')]) == 'cpu;desc="a \\"b\\" \\\\ c"'


def test_empty_description_is_quoted() -> None:
    assert build([Metric("cpu", desc="")]) == 'cpu;desc=""'


def test_tab_and_latin1_text_are_allowed_inside_quotes() -> None:
    assert build([Metric("cpu", desc="caf\xe9\tok")]) == 'cpu;desc="caf\xe9\tok"'


@pytest.mark.parametrize("bad", ["a\r\nSet-Cookie: x=1", "a\nb", "a\rb", "\x00", "\x7f", "\x1b"])
def test_build_refuses_a_description_that_could_split_the_header(bad: str) -> None:
    with pytest.raises(ServerTimingError, match="no HTTP field value can carry"):
        build([Metric("cpu", desc=bad)])


def test_build_refuses_characters_beyond_one_octet() -> None:
    with pytest.raises(ServerTimingError):
        build([Metric("cpu", desc="snow ☃")])


@pytest.mark.parametrize("name", ["", "bad name", "a;b", "a,b", 'a"', "caf\xe9", "a\r\nb"])
def test_build_rejects_a_name_that_is_not_a_token(name: str) -> None:
    with pytest.raises(ServerTimingError):
        build([Metric(name)])


@pytest.mark.parametrize("dur", [float("inf"), float("-inf"), float("nan"), 10**400])
def test_build_rejects_a_non_finite_duration(dur: float) -> None:
    with pytest.raises(ServerTimingError):
        build([Metric("cpu", dur=dur)])


@pytest.mark.parametrize("dur", [True, "5", None.__class__])
def test_build_rejects_a_duration_that_is_not_a_number(dur: object) -> None:
    with pytest.raises(TypeError, match="duration must be an int or a float"):
        build([Metric("cpu", dur=dur)])  # type: ignore[arg-type]


def test_build_rejects_a_description_that_is_not_a_str() -> None:
    with pytest.raises(TypeError, match="description must be a str"):
        build([Metric("cpu", desc=5)])  # type: ignore[arg-type]


def test_build_rejects_something_that_is_not_a_metric() -> None:
    with pytest.raises(TypeError, match="expected a Metric"):
        build(["cpu"])  # type: ignore[list-item]
    with pytest.raises(TypeError, match="wrap one metric in a list"):
        build("cpu")  # type: ignore[arg-type]


def test_extension_parameters_are_written_after_dur_and_desc() -> None:
    metric = Metric("cdn", 4.0, "edge", (("hit", "1"), ("pop", "MAD 2")))
    assert build([metric]) == 'cdn;dur=4;desc=edge;hit=1;pop="MAD 2"'
    assert str(metric) == 'cdn;dur=4;desc=edge;hit=1;pop="MAD 2"'


@pytest.mark.parametrize(
    "params",
    [
        (("bad name", "1"),),
        (("dur", "1"),),
        (("DESC", "x"),),
        (("hit", "1"), ("HIT", "2")),
        (("hit", "a\nb"),),
    ],
)
def test_build_rejects_bad_extension_parameters(params: object) -> None:
    with pytest.raises(ServerTimingError):
        build([Metric("cdn", params=params)])  # type: ignore[arg-type]


@pytest.mark.parametrize("params", [(("hit", 1),), ((1, "1"),), (("hit",),), ("hit",)])
def test_build_rejects_extension_parameters_of_the_wrong_type(params: object) -> None:
    with pytest.raises(TypeError):
        build([Metric("cdn", params=params)])  # type: ignore[arg-type]


def test_the_error_is_a_value_error_without_a_position() -> None:
    with pytest.raises(ValueError) as caught:
        build([Metric("bad name")])
    assert isinstance(caught.value, ServerTimingError)
    assert caught.value.position is None
    assert caught.value.field is None


def test_precision_drops_trailing_zeros() -> None:
    assert build([Metric("cpu", dur=12.5), Metric("io", dur=3.0)], precision=3) == (
        "cpu;dur=12.5, io;dur=3"
    )

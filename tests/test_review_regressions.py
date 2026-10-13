"""Regression tests for the findings of the independent review."""

from __future__ import annotations

import asyncio
import io
import threading

import pytest

from servertiming import Metric, ServerTimingError, Timing, build, parse
from servertiming._cli import fields_from_lines, main


def test_parameter_names_round_trip_whatever_their_case() -> None:
    metric = Metric("a", params=(("Foo", "x"),))
    assert metric.params == (("foo", "x"),)
    assert metric.param("FOO") == "x"
    assert parse(build([metric]), strict=True) == [metric]


def test_an_int_duration_is_stored_as_the_float_that_is_sent() -> None:
    metric = Metric("a", dur=2**53 + 1)
    assert isinstance(metric.dur, float)
    assert parse(build([metric]), strict=True) == [metric]


def test_a_huge_int_duration_is_left_for_build_to_reject() -> None:
    with pytest.raises(ServerTimingError):
        build([Metric("a", dur=10**400)])


def _race_to_stop() -> tuple[list[str], int]:
    timing = Timing()
    timer = timing.start("t")
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def stop() -> None:
        barrier.wait()
        try:
            timer.stop()
            outcomes.append("ok")
        except RuntimeError:
            outcomes.append("refused")

    threads = [threading.Thread(target=stop) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return sorted(outcomes), len(timing.metrics)


def test_a_timer_stopped_from_two_threads_records_once() -> None:
    for _ in range(200):
        assert _race_to_stop() == (["ok", "refused"], 1)


def test_one_measure_entered_by_overlapping_tasks_keeps_their_starts_apart() -> None:
    now = [0.0]
    timing = Timing(clock=lambda: now[0])
    shared = timing.measure("job")
    gates = {name: asyncio.Event() for name in ("a_in", "b_in", "a_out")}

    async def task_a() -> None:
        with shared:
            gates["a_in"].set()
            await gates["b_in"].wait()
            now[0] = 0.010
        gates["a_out"].set()

    async def task_b() -> None:
        await gates["a_in"].wait()
        now[0] = 0.005
        with shared:
            gates["b_in"].set()
            await gates["a_out"].wait()
            now[0] = 0.020

    async def run() -> None:
        await asyncio.gather(task_a(), task_b())

    asyncio.run(run())
    assert sorted(m.dur for m in timing.metrics if m.dur is not None) == pytest.approx([10, 15])


def test_strict_rejects_the_empty_elements_a_sender_must_not_write() -> None:
    assert parse("a,,b") == [Metric("a"), Metric("b")]
    with pytest.raises(ServerTimingError, match="empty list element"):
        parse("a,,b", strict=True)


def test_headers_without_server_timing_give_no_value(capsys: pytest.CaptureFixture[str]) -> None:
    raw = "HTTP/2 200\r\ncontent-type: text/html\r\ncache-control: max-age=0\r\n\r\n"
    assert main([], stdin=io.StringIO(raw)) == 2
    out, err = capsys.readouterr()
    assert out == ""
    assert "no Server-Timing value" in err


def test_a_response_body_after_the_headers_is_ignored() -> None:
    lines = ["HTTP/1.1 200 OK", "Server-Timing: a", "", "<html>", "body; text"]
    assert fields_from_lines(lines) == ["a"]


def test_folded_continuation_lines_join_their_field() -> None:
    lines = ["HTTP/1.1 200 OK", "Server-Timing: a;dur=1,", " b;dur=2", "X: y", " z"]
    assert fields_from_lines(lines) == ["a;dur=1, b;dur=2"]


def test_stdin_lines_split_only_on_line_feeds(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([], stdin=io.StringIO('a;desc="x\x85y", b\n')) == 0
    assert "'x\\x85y'" in capsys.readouterr().out


def test_unprintable_output_is_escaped_not_a_traceback(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    target = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr("sys.stdout", target)
    assert main(['a;desc="x\u0100"']) == 1
    target.seek(0)
    assert "'x\\u0100'" in target.read()


def test_parse_keeps_the_header_keyword() -> None:
    assert parse(header="db") == [Metric("db")]


def test_parse_explains_how_to_pass_bytes() -> None:
    with pytest.raises(TypeError, match="latin-1"):
        parse(b"db")  # type: ignore[arg-type]


def test_build_explains_that_it_takes_a_list() -> None:
    with pytest.raises(ServerTimingError, match="wrap one metric in a list"):
        build(Metric("db"))  # type: ignore[arg-type]

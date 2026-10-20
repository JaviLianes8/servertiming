from __future__ import annotations

import io
import json
import runpy
import sys

import pytest

from timingheader._cli import main


def test_values_are_shown_as_a_table_and_valid_input_exits_zero(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = main(["miss, db;dur=53", 'cache;desc="Cache Read";dur=23.25;hit=1'])
    out, err = capsys.readouterr()
    assert code == 0
    assert err == ""
    assert out.splitlines() == [
        "name     dur  desc",
        "miss",
        "db        53",
        "cache  23.25  'Cache Read' hit='1'",
    ]


def test_invalid_input_is_reported_and_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["ok", "db;desc=d1 d2"])
    out, err = capsys.readouterr()
    assert code == 1
    assert "d1" in out
    assert err.strip() == "invalid value 2: expected ',' or ';' at position 11 (found 'd')"


def test_response_headers_on_stdin_use_only_server_timing_lines(
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw = (
        "HTTP/1.1 200 OK\r\nServer-Timing: a;dur=1\r\nX-Other: b;dur=2\r\nserver-timing: c\r\n\r\n"
    )
    code = main(["--json"], stdin=io.StringIO(raw))
    out, _ = capsys.readouterr()
    assert code == 0
    assert json.loads(out) == [
        {"name": "a", "dur": 1.0, "desc": None, "params": {}},
        {"name": "c", "dur": None, "desc": None, "params": {}},
    ]


def test_plain_lines_on_stdin_are_values(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([], stdin=io.StringIO("a;dur=1\n\nb\n")) == 0
    assert [line.split()[0] for line in capsys.readouterr().out.splitlines()] == ["name", "a", "b"]


def test_no_input_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([], stdin=io.StringIO(" \n")) == 2
    assert "no Server-Timing value" in capsys.readouterr().err


def test_python_dash_m_runs_the_command(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "argv", ["timingheader", "x;dur=2"])
    with pytest.raises(SystemExit) as caught:
        runpy.run_module("timingheader", run_name="__main__")
    assert caught.value.code == 0
    assert "x" in capsys.readouterr().out

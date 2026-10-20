"""Contracts for where the command writes and how it numbers stdin values, QA round 2."""

from __future__ import annotations

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from timingheader._cli import fields_from_lines, main

SRC = Path(__file__).resolve().parents[1] / "src"


def _command(*args: str, **kwargs: object) -> subprocess.Popen[bytes]:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(SRC), env.get("PYTHONPATH")]))
    return subprocess.Popen(  # type: ignore[call-overload, no-any-return]
        [sys.executable, "-m", "timingheader", *args], env=env, **kwargs
    )


@pytest.mark.parametrize(
    ("args", "code"),
    [(["db;dur=1"], 0), (["--json", "db;dur=1"], 0), (["db;desc=d1 d2"], 1)],
)
def test_a_reader_closed_before_a_small_write_gets_no_traceback(args: list[str], code: int) -> None:
    read_end, write_end = os.pipe()
    os.close(read_end)
    try:
        proc = _command(*args, stdin=subprocess.DEVNULL, stdout=write_end, stderr=subprocess.PIPE)
    finally:
        os.close(write_end)
    _, err = proc.communicate(timeout=120)
    assert b"Traceback" not in err and b"Exception" not in err, err[-2000:]
    assert proc.returncode == code


@pytest.mark.parametrize(("args", "code"), [(["db;dur=1"], 0), (["db;desc=d1 d2"], 1)])
def test_no_stdout_at_all_is_like_a_reader_that_stopped(
    args: list[str], code: int, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # sys.stdout is None under pythonw, in a service, or with file descriptor 1 closed.
    monkeypatch.setattr(sys, "stdout", None)
    assert main(args) == code
    assert ("invalid value 1" in capsys.readouterr().err) is (code == 1)


def test_values_read_from_stdin_are_numbered_in_order_from_one(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([], stdin=io.StringIO("ok\n\ndb;desc=d1 d2\nfine\n")) == 1
    err = capsys.readouterr().err
    assert err.strip() == "invalid value 2: expected ',' or ';' at position 11 (found 'd')"


def test_only_the_last_of_two_http_1_1_responses_is_read() -> None:
    dump = (
        "HTTP/1.1 301 Moved\r\nServer-Timing: cache;desc=hit\r\nLocation: /x\r\n\r\n"
        "HTTP/1.1 200 OK\r\nServer-Timing: total;dur=5\r\n\r\n"
    )
    lines = [line.removesuffix("\r") for line in dump.split("\n")]
    assert fields_from_lines(lines) == ["total;dur=5"]


def test_the_command_shows_only_the_last_http_1_1_response(
    capsys: pytest.CaptureFixture[str],
) -> None:
    dump = "HTTP/1.1 301 Moved\nServer-Timing: cache\n\nHTTP/1.1 200 OK\nServer-Timing: total\n"
    assert main([], stdin=io.StringIO(dump)) == 0
    assert capsys.readouterr().out.split() == ["name", "dur", "desc", "total"]

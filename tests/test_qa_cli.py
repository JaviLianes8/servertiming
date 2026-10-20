"""Contracts for the command line, from the 1.0.0 QA round."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from timingheader._cli import fields_from_lines, main

SRC = Path(__file__).resolve().parents[1] / "src"


def _command(*args: str, **kwargs: object) -> subprocess.Popen[bytes]:
    env = dict(os.environ)
    # The source tree when there is one; an installed package otherwise.
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(SRC), env.get("PYTHONPATH")]))
    return subprocess.Popen(  # type: ignore[call-overload, no-any-return]
        [sys.executable, "-m", "timingheader", *args], env=env, **kwargs
    )


def _run(*args: str, stdin: bytes) -> tuple[int, bytes, bytes]:
    proc = _command(*args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate(stdin, timeout=120)
    return proc.returncode, out, err


@pytest.mark.parametrize("values", [["  "], ["", " "], ["\t"]])
def test_blank_values_alone_exit_two(values: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(values) == 2
    out, err = capsys.readouterr()
    assert out == "" and "no Server-Timing value given" in err


def test_invalid_values_are_numbered_by_their_place_on_the_command_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["", "ok", " ", "db;desc=d1 d2"]) == 1
    err = capsys.readouterr().err
    assert err.strip() == "invalid value 4: expected ',' or ';' at position 11 (found 'd')"


def test_a_status_line_alone_on_stdin_is_a_response_without_the_header(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main([], stdin=io.StringIO("HTTP/1.1 204 No Content\r\n\r\n")) == 2
    out, err = capsys.readouterr()
    assert out == "" and "no Server-Timing value given" in err


def test_only_the_last_response_of_a_dump_with_redirects_is_read() -> None:
    dump = [
        "HTTP/1.1 301 Moved Permanently",
        "Server-Timing: cache;desc=hit, host;desc=a",
        "Location: https://example.org/",
        "",
        "HTTP/2 200",
        "server-timing: total;dur=5",
        "server-timing: db;",
        " dur=2",
        "",
    ]
    assert fields_from_lines(dump) == ["total;dur=5", "db; dur=2"]
    assert fields_from_lines(dump[:4]) == ["cache;desc=hit, host;desc=a"]


def _ascii_stdout(monkeypatch: pytest.MonkeyPatch, encoding: str) -> io.BytesIO:
    raw = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(raw, encoding=encoding, newline="\n"))
    return raw


@pytest.mark.parametrize("encoding", ["cp1252", "ascii", "utf-8"])
def test_json_output_is_valid_json_whatever_stdout_can_encode(
    encoding: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _ascii_stdout(monkeypatch, encoding)
    assert main(["--json", 'a;desc="\x85 caf\xe9"']) == 0
    sys.stdout.flush()
    text = raw.getvalue().decode(encoding)
    assert json.loads(text) == [{"name": "a", "dur": None, "desc": "\x85 caf\xe9", "params": {}}]
    assert '"desc": "\\u0085 caf\\u00e9"' in text


def test_json_output_text_is_pinned(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--json", 'db;dur=1;desc="caf\xe9";hit=1']) == 0
    assert capsys.readouterr().out == (
        "[\n"
        "  {\n"
        '    "name": "db",\n'
        '    "dur": 1.0,\n'
        '    "desc": "caf\\u00e9",\n'
        '    "params": {\n'
        '      "hit": "1"\n'
        "    }\n"
        "  }\n"
        "]\n"
    )


def test_stdin_is_read_as_iso_8859_1() -> None:
    code, out, err = _run("--json", stdin=b'Server-Timing: db;desc="caf\xe9"\r\n')
    assert (code, err) == (0, b"")
    assert json.loads(out) == [{"name": "db", "dur": None, "desc": "caf\xe9", "params": {}}]


def test_a_reader_that_closes_early_gets_no_traceback(tmp_path: Path) -> None:
    source = tmp_path / "big.txt"
    source.write_text(", ".join(f"m{i};dur={i}" for i in range(200_000)) + "\n", encoding="ascii")
    with source.open("rb") as stdin:
        proc = _command(stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.stdout is not None and proc.stderr is not None
        assert proc.stdout.readline().split() == [b"name", b"dur", b"desc"]
        proc.stdout.close()
        err = proc.stderr.read()
        proc.wait(timeout=120)
    assert b"Traceback" not in err and b"Error" not in err, err[-2000:]
    assert proc.returncode == 0


@pytest.mark.parametrize("fold", [b"\t", b" ", b" \t"])
def test_a_line_folded_with_a_tab_or_a_space_continues_the_field(fold: bytes) -> None:
    raw = b"HTTP/1.1 200 OK\r\nServer-Timing: db;dur=1,\r\n" + fold + b"cache;desc=hit\r\n\r\n"
    code, out, err = _run("--json", stdin=raw)
    assert (code, err) == (0, b"")
    assert json.loads(out) == [
        {"name": "db", "dur": 1.0, "desc": None, "params": {}},
        {"name": "cache", "dur": None, "desc": "hit", "params": {}},
    ]
    assert fields_from_lines(["Server-Timing: a", "\tb"]) == ["a b"]

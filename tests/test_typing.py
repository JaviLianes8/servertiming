"""The public API is typed: mypy infers the documented types and rejects wrong ones."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "src"

SNIPPET = """
from timingheader import Metric, Timing, build, parse
timing = Timing()
reveal_type(parse("db"))
reveal_type(parse(["db", "x"], strict=True)[0].dur)
reveal_type(Metric("db").params)
reveal_type(Metric("db").duration)
reveal_type(build([Metric("db")], precision=2))
reveal_type(timing.start("db").stop())
@timing.measure("work")
def work(x: int) -> str:
    return str(x)
reveal_type(work)
async def fetch() -> bytes:
    return b""
reveal_type(timing.measure("io")(fetch))
parse(b"db")
build([Metric("db")], precision=1.5)
Metric("db", dur="5")
parse("db", True)
work("x")
"""


@pytest.fixture(scope="module")
def mypy_output(tmp_path_factory: pytest.TempPathFactory) -> str:
    folder = tmp_path_factory.mktemp("typing")
    target = folder / "snippet.py"
    target.write_text(SNIPPET, encoding="utf-8")
    config = folder / "mypy.ini"
    config.write_text(f"[mypy]\nmypy_path = {SRC.as_posix()}\n", encoding="utf-8")
    cache = str(folder / "cache")
    args = ["--strict", "--config-file", str(config), "--cache-dir", cache, str(target)]
    try:
        from mypy import api
    except ImportError:
        # The interpreter running pytest may lack mypy while the one on PATH has it.
        program = shutil.which("mypy")
        if program is None:
            pytest.skip("mypy is not installed")
        result = subprocess.run([program, *args], capture_output=True, text=True, check=False)
        return result.stdout + result.stderr
    out, err, _ = api.run(args)
    return str(out) + str(err)


def test_functions_return_the_documented_types(mypy_output: str) -> None:
    lines = (4, 5, 6, 7, 8, 9, 13, 16)
    assert [_revealed(mypy_output, line) for line in lines] == [
        "list[timingheader._metric.Metric]",
        "float | None",
        "tuple[tuple[str, str], ...]",
        "float",
        "str",
        "timingheader._metric.Metric",
        "def (x: int) -> str",
        "def () -> Coroutine[Any, Any, bytes]",
    ]


def test_misuse_is_rejected(mypy_output: str) -> None:
    expected = (
        (17, "arg-type"),
        (18, "arg-type"),
        (19, "arg-type"),
        (20, "call-arg"),
        (21, "arg-type"),
    )
    for line, code in expected:
        assert re.search(rf"snippet\.py:{line}: error: .*\[{code}\]", mypy_output), mypy_output
    assert mypy_output.count(": error: ") == len(expected), mypy_output


def _revealed(output: str, line: int) -> str:
    match = re.search(rf"snippet\.py:{line}: note: Revealed type is \"(.+)\"", output)
    assert match, output
    # Older mypy releases spell builtins with their module prefix.
    return re.sub(r"\b(builtins|typing|collections\.abc)\.", "", match.group(1))

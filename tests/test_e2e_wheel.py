"""Build the wheel, install it in a throwaway venv and drive the installed package.

Slow and needs the build backend, so it runs only with TIMINGHEADER_E2E=1.
"""

from __future__ import annotations

import os
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.skipif(
    os.environ.get("TIMINGHEADER_E2E") != "1", reason="set TIMINGHEADER_E2E=1 to build and install"
)

PROGRAM = r"""
import asyncio, importlib.metadata, importlib.resources, pickle
import timingheader
from timingheader import Metric, ServerTimingError, Timing, build, parse

assert "site-packages" in timingheader.__file__, timingheader.__file__
assert importlib.metadata.version("timingheader") == timingheader.__version__
assert importlib.resources.files("timingheader").joinpath("py.typed").is_file()
assert parse('db;desc=d1 d2;dur=12ms, [x], miss;DUR=1;dur=2') == [
    Metric("db", 12.0, "d1"), Metric("miss", 1.0)
]
assert parse(["a", 'b;desc="x"', "total;dur=9"], strict=True)[2] == Metric("total", 9.0)
try:
    parse("db;dur=1;dur=2", strict=True)
except ServerTimingError as error:
    copy = pickle.loads(pickle.dumps(error))
    assert (copy.position, copy.field) == (9, 0), (copy.position, copy.field)
else:
    raise AssertionError("strict accepted a repeated parameter")
try:
    build([Metric("db", desc="a\r\nSet-Cookie: x=1")])
except ServerTimingError:
    pass
else:
    raise AssertionError("build wrote a CRLF")
metric = Metric("cdn", 4.25, 'a "b"', (("hit", "1"),))
assert str(metric) == 'cdn;dur=4.25;desc="a \\"b\\"";hit=1', str(metric)
assert parse(build([metric]), strict=True) == [metric]
timing = Timing()

@timing.measure("io")
async def io():
    await asyncio.sleep(0.01)

asyncio.run(io())
timing.start("t").stop()
assert [m.name for m in timing.metrics] == ["io", "t"]
assert timing.metrics[0].dur >= 5.0, timing.metrics
assert Metric.__module__ == "timingheader" and timingheader.__version__ == "1.0.0"
def gen():
    yield 1

for call in (lambda: build("db"), lambda: Metric("a").param(1), lambda: timing.measure("g")(gen)):
    try:
        call()
    except TypeError:
        pass
    else:
        raise AssertionError("no TypeError")
print("e2e ok")
"""


def _run(
    *cmd: str | Path, cwd: Path | None = None, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(c) for c in cmd], cwd=cwd, capture_output=True, text=True, input=stdin, check=False
    )


def test_installed_wheel_end_to_end(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    built = _run(sys.executable, "-m", "build", "--outdir", dist, ROOT)
    assert built.returncode == 0, built.stderr
    (wheel,) = dist.glob("timingheader-*.whl")
    (sdist,) = dist.glob("timingheader-*.tar.gz")
    names = zipfile.ZipFile(wheel).namelist()
    assert "timingheader/py.typed" in names
    assert "timingheader/__main__.py" in names
    assert not any(name.startswith("tests/") for name in names)
    assert any(name.endswith("entry_points.txt") for name in names)
    assert any(name.endswith("licenses/LICENSE") for name in names), names
    listing = _run(sys.executable, "-m", "tarfile", "-l", sdist).stdout
    for absent in ("IMPROVEMENTS-round", "CERT-1.0", ".js.sub.headers", "rfc9110.txt", "docs/"):
        assert absent not in listing, absent
    for present in ("tests/upstream/MANIFEST.json", "tests/test_wpt.py", "GUIDE.md", "LICENSE"):
        assert present in listing, present
    assert "scripts/fetch_upstream.py" in listing
    checked = _run(sys.executable, "-m", "twine", "check", "--strict", wheel, sdist)
    assert checked.returncode == 0, checked.stdout + checked.stderr

    env_dir = tmp_path / "venv"
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if sys.platform == "win32" else "bin")
    python = bindir / "python"
    installed = _run(python, "-m", "pip", "install", "-q", wheel)
    assert installed.returncode == 0, installed.stderr

    # Run from an empty folder so the source tree cannot shadow the install.
    work = tmp_path / "work"
    work.mkdir()
    result = _run(python, "-I", "-c", PROGRAM, cwd=work)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "e2e ok"

    script = bindir / ("timingheader.exe" if sys.platform == "win32" else "timingheader")
    headers = "HTTP/1.1 200 OK\nServer-Timing: db;dur=53\nServer-Timing: x;\n"
    checked = _run(script, cwd=work, stdin=headers)
    assert checked.returncode == 1, checked.stderr
    assert checked.stdout.splitlines()[1].split() == ["db", "53"]
    assert "invalid value 2" in checked.stderr
    module = _run(python, "-I", "-m", "timingheader", "--json", "a;dur=1", cwd=work)
    assert module.returncode == 0, module.stderr
    assert '"dur": 1.0' in module.stdout
    table = _run(script, 'db;dur=53, cache;desc="Cache Read";dur=23.2', cwd=work)
    assert table.returncode == 0 and table.stdout.split() == [
        "name",
        "dur",
        "desc",
        "db",
        "53",
        "cache",
        "23.2",
        "'Cache",
        "Read'",
    ], table.stdout
    empty = _run(script, cwd=work, stdin="HTTP/1.1 200 OK\nContent-Type: text/html\n")
    assert empty.returncode == 2 and "no Server-Timing value" in empty.stderr

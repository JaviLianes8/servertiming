"""Every documented example type-checks as consumer code under mypy --strict."""

from __future__ import annotations

import doctest
import importlib
import pkgutil
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import timingheader

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


def _doctest_sources() -> dict[str, str]:
    found: dict[str, str] = {}
    finder = doctest.DocTestFinder()
    names = [timingheader.__name__] + [
        f"{timingheader.__name__}.{info.name}"
        for info in pkgutil.iter_modules(timingheader.__path__)
    ]
    for module_name in names:
        for test in finder.find(importlib.import_module(module_name)):
            if test.examples:
                found[test.name] = "".join(example.source for example in test.examples)
    return found


def _markdown_sources() -> dict[str, str]:
    found: dict[str, str] = {}
    for name in ("README.md", "GUIDE.md"):
        path = ROOT / name
        if not path.is_file():
            continue
        blocks = re.findall(r"```python\n(.*?)```", path.read_text(encoding="utf-8"), re.DOTALL)
        for index, block in enumerate(blocks):
            found[f"{name}#{index}"] = block
    return found


def _mypy(folder: Path, files: list[Path]) -> str:
    config = folder / "mypy.ini"
    path = f"mypy_path = {SRC.as_posix()}\n" if SRC.is_dir() else ""
    config.write_text(f"[mypy]\n{path}", encoding="utf-8")
    args = ["--strict", "--config-file", str(config), "--cache-dir", str(folder / "cache")]
    args += [str(file) for file in files]
    try:
        from mypy import api
    except ImportError:
        program = shutil.which("mypy")
        if program is None:
            pytest.skip("mypy is not installed")
        command = [program, "--python-executable", sys.executable, *args]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.stdout + result.stderr
    out, err, _ = api.run(args)
    return str(out) + str(err)


def test_every_documented_example_passes_mypy_strict(tmp_path: Path) -> None:
    sources = {**_doctest_sources(), **_markdown_sources()}
    assert len(sources) >= 20, sorted(sources)
    files = []
    origin = {}
    for index, (name, source) in enumerate(sorted(sources.items())):
        file = tmp_path / f"example_{index:03}.py"
        file.write_text(source, encoding="utf-8")
        files.append(file)
        origin[file.name] = name
    output = _mypy(tmp_path, files)
    errors = [line for line in output.splitlines() if ": error: " in line]
    for line in errors:
        match = re.search(r"example_\d+\.py", line)
        errors[errors.index(line)] = f"{origin.get(match.group(0) if match else '', '?')}: {line}"
    assert not errors, "\n".join(errors)

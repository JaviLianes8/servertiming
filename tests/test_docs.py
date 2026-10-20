"""The README examples run and print what their comments say; docs and versions agree."""

from __future__ import annotations

import contextlib
import io
import re
from pathlib import Path

import pytest

import timingheader
from timingheader._cli import main

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
GUIDE = (ROOT / "GUIDE.md").read_text(encoding="utf-8")
BADGE = (
    "[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)]"
    "(https://lianes8studio.com/certified)"
)


def _python_blocks(text: str = README) -> list[str]:
    return re.findall(r"```python\n(.*?)```", text, flags=re.DOTALL)


def _expected_output(block: str) -> list[str]:
    """The comment lines that follow the last print of a block are what the block prints."""
    lines = block.splitlines()
    expected: list[str] = []
    for index, line in enumerate(lines):
        previous = lines[index - 1].strip() if index else ""
        if line.startswith("# ") and previous.startswith(("print(", "# ")):
            expected.append(line[2:])
    return expected


@pytest.mark.parametrize(("name", "blocks", "outputs"), [("README", 6, 9), ("GUIDE", 5, 11)])
def test_every_example_runs_and_prints_its_comments(name: str, blocks: int, outputs: int) -> None:
    text = README if name == "README" else GUIDE
    checked = 0
    for block in _python_blocks(text):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            exec(compile(block, f"{name}.md", "exec"), {"__name__": name.lower()})
        expected = _expected_output(block)
        assert expected, block
        assert out.getvalue().splitlines() == expected
        checked += len(expected)
    assert len(_python_blocks(text)) == blocks
    assert checked == outputs


def test_the_readme_links_are_absolute_and_carry_the_badge() -> None:
    assert README.splitlines()[2] == BADGE
    for target in re.findall(r"\]\(([^)]+)\)", README):
        assert target.startswith("https://"), target
    assert "https://github.com/JaviLianes8/timingheader/blob/main/GUIDE.md" in README
    assert "https://github.com/JaviLianes8/timingheader/blob/main/CHANGELOG.md" in README


def test_every_print_in_the_readme_shows_its_output() -> None:
    for block in _python_blocks():
        prints = [line for line in block.splitlines() if line.strip().startswith("print(")]
        assert len(prints) == len(_expected_output(block)), block


def test_the_command_line_example_prints_what_the_readme_shows() -> None:
    shell = README.split("## Command line", 1)[1].split("```", 2)[1]
    command = "$ timingheader 'db;dur=53, cache;desc=\"Cache Read\";dur=23.2'\n"
    shown = shell.split(command, 1)[1].split("$ ", 1)[0].splitlines()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        assert main(['db;dur=53, cache;desc="Cache Read";dur=23.2']) == 0
    assert out.getvalue().splitlines() == shown


def test_the_api_table_lists_every_public_name() -> None:
    table = README.split("## API", 1)[1].split("\n## ", 1)[0]
    for name in timingheader.__all__:
        assert f"`{name}" in table, name


def test_version_matches_pyproject() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, flags=re.MULTILINE)
    assert match is not None
    assert match.group(1) == timingheader.__version__


def test_changelog_has_an_entry_for_this_version() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## [{timingheader.__version__}]" in text


def _tracked_text_files() -> list[Path]:
    suffixes = {".py", ".md", ".toml", ".ps1", ".txt", ".json", ".yml", ".cfg"}
    found = []
    for path in ROOT.rglob("*"):
        parts = path.relative_to(ROOT).parts
        if not path.is_file() or path.suffix not in suffixes:
            continue
        if parts[:2] == ("tests", "upstream") and path.name != "MANIFEST.json":
            continue
        if any(part.startswith(".") or part in ("__pycache__", "build", "dist") for part in parts):
            continue
        found.append(path)
    return found


def test_no_em_dash_anywhere_in_the_tree() -> None:
    for path in _tracked_text_files():
        assert chr(0x2014) not in path.read_text(encoding="utf-8"), path


def test_source_files_stay_under_two_hundred_lines() -> None:
    for path in [*(ROOT / "src").rglob("*.py"), *(ROOT / "tests").glob("*.py")]:
        lines = path.read_text(encoding="utf-8").count("\n")
        assert lines <= 200, path

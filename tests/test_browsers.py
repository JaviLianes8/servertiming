"""Real browser engines as the oracle: what they expose for the same response headers.

Each case is sent by a local server as real ``Server-Timing`` response headers and read
back from ``PerformanceResourceTiming.serverTiming`` (``tests/browser_oracle.py``). The
engines are the installed Google Chrome and Firefox and Playwright's WebKit. Slow, and
needs Playwright and the browsers, so it runs only with TIMINGHEADER_BROWSERS=1;
TIMINGHEADER_BROWSER_ENGINES picks the engines (default ``chrome,webkit,firefox``).

On every header that follows the grammar, and on the web-platform-tests corpus, every
engine exposes exactly what ``parse`` gives. On malformed text the engines disagree with
one another; ``DIFFERENCES`` pins what each one did on 2026-10-20 (Chrome 155, WebKit of
Playwright 1.64, Firefox 158), recorded from their output, so the GUIDE stays true.
"""

from __future__ import annotations

import os
import random

import pytest
from conftest import read_upstream, upstream_manifest
from generators import valid_field

from timingheader import parse

pytestmark = pytest.mark.skipif(
    os.environ.get("TIMINGHEADER_BROWSERS") != "1",
    reason="set TIMINGHEADER_BROWSERS=1 to compare with real browsers",
)
ENGINES = os.environ.get("TIMINGHEADER_BROWSER_ENGINES", "chrome,webkit,firefox").split(",")
CASES = int(os.environ.get("TIMINGHEADER_BROWSER_CASES", "3000"))

# What each engine exposed for these field values (recorded output, see the docstring).
# "ours" is what parse gives: the W3C algorithm as the web-platform-tests corpus reads it.
_A, _B = ("a", 0.0, ""), ("b", 0.0, "")
DIFFERENCES: dict[str, dict[str, list[tuple[str, float, str]]]] = {
    "a,,b": {"chrome": [_A], "webkit": [_A], "firefox": [_A, _B], "ours": [_A, _B]},
    "[x], b": {"chrome": [], "webkit": [], "firefox": [_B], "ours": [_B]},
    "a;=1, b": {"chrome": [_A], "webkit": [_A], "firefox": [_A, _B], "ours": [_A, _B]},
    "a;;dur=1": {
        "chrome": [_A],
        "webkit": [_A],
        "firefox": [("a", 1.0, "")],
        "ours": [("a", 1.0, "")],
    },
    "a=1, b": {"chrome": [_A, _B], "webkit": [_A], "firefox": [_A, _B], "ours": [_A, _B]},
    "a;dur=12ms": {
        "chrome": [_A],
        "webkit": [("a", 12.0, "")],
        "firefox": [_A],
        "ours": [("a", 12.0, "")],
    },
    "a;dur=1e309": {
        "chrome": [("a", float("inf"), "")],
        "webkit": [("a", float("inf"), "")],
        "firefox": [_A],
        "ours": [_A],
    },
}


# The corpus cases an engine reads differently from the corpus (and so from parse).
CORPUS_MISSES = {"webkit": {'metric==   ""foo;dur=123.4', 'metric1==   ""foo,metric2'}}


def _ours(fields: list[str]) -> list[tuple[str, float, str]]:
    return [(m.name, m.duration, m.description) for m in parse(fields)]


def _views(cases: list[list[str]], engine: str) -> list[list[tuple[str, float, str]]]:
    pytest.importorskip("playwright.sync_api")
    from browser_oracle import browser_views

    views = browser_views(cases, engine)
    missing = [cases[index] for index, view in enumerate(views) if view is None]
    assert not missing, f"{engine} exposed no entry for {missing[:3]}"
    return [view for view in views if view is not None]


@pytest.mark.parametrize("engine", ENGINES)
def test_every_engine_reads_valid_headers_as_parse_does(engine: str) -> None:
    rng = random.Random(20261020)
    # Firefox decodes obs-text as UTF-8, the others as ISO-8859-1 as parse does; it gets
    # ASCII values only. WebKit exposes only the last of several fields, so it gets one
    # field per response. Both differences are pinned below and listed in the GUIDE.
    ascii_only = engine == "firefox"
    counts = [1] if engine == "webkit" else [1, 1, 2, 3]
    cases: list[list[str]] = []
    while len(cases) < CASES:
        fields = [valid_field(rng).strip(" \t") for _ in range(rng.choice(counts))]
        if not ascii_only or all(text.isascii() for text in fields):
            cases.append(fields)
    views = _views(cases, engine)
    differ = [(c, v, _ours(c)) for c, v in zip(cases, views, strict=True) if v != _ours(c)]
    assert not differ, f"{len(differ)} of {len(cases)} differ from {engine}: {differ[:3]}"
    assert parse(cases[0], strict=True)


@pytest.mark.parametrize("engine", ENGINES)
def test_every_engine_reads_the_corpus_as_parse_does(engine: str) -> None:
    names = sorted({name.split(".", 1)[0] for name in upstream_manifest()["files"]}, key=int)
    cases: list[list[str]] = []
    for name in names:
        headers = read_upstream(f"{name}.js.sub.headers").splitlines()
        lines = [line for line in headers if line.lower().startswith("server-timing:")]
        cases.append([line.split(":", 1)[1].strip(" \t") for line in lines])
    views = _views(cases, engine)
    differ = [", ".join(c) for c, v in zip(cases, views, strict=True) if v != _ours(c)]
    assert set(differ) == CORPUS_MISSES.get(engine, set()), (engine, differ)


@pytest.mark.parametrize("engine", ENGINES)
def test_the_recorded_differences_still_hold(engine: str) -> None:
    inputs = sorted(DIFFERENCES)
    views = _views([[text] for text in inputs], engine)
    for text, view in zip(inputs, views, strict=True):
        assert view == DIFFERENCES[text][engine], (engine, text, view)
        assert _ours([text]) == DIFFERENCES[text]["ours"], text


@pytest.mark.parametrize("engine", ENGINES)
def test_several_fields_and_text_beyond_ascii(engine: str) -> None:
    fields = ["a;dur=1", "b;dur=2", "c"]
    (view,) = _views([fields], engine)
    assert view == ([("c", 0.0, "")] if engine == "webkit" else _ours(fields)), engine
    latin = "caf" + chr(0xE9)
    (view,) = _views([[f'a;desc="{latin}"']], engine)
    shown = "caf" + chr(0xFFFD) if engine == "firefox" else latin
    assert view == [("a", 0.0, shown)] and _ours([f'a;desc="{latin}"'])[0][2] == latin

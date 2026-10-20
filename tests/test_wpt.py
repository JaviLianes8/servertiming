"""The web-platform-tests Server-Timing parsing corpus, read the way browsers read it.

Files: `server-timing/resources/parsing/<n>.js` (the metrics a browser must expose) and
`<n>.js.sub.headers` (the response header sent) from web-platform-tests; URL, commit,
sizes and sha256 are in tests/upstream/MANIFEST.json. They are not committed; these tests
skip until `python scripts/fetch_upstream.py` has fetched them. The runner page compares
name, duration (0 when absent) and description ("" when absent) of every entry.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest
from conftest import read_upstream, upstream_manifest

from timingheader import parse

CASES = sorted(
    {name.split(".", 1)[0] for name in upstream_manifest()["files"]}, key=lambda n: int(n)
)
_EXPECTED = re.compile(r"testServerTiming\(document\.currentScript, (.*)\)\s*$", re.DOTALL)


def _case(number: str) -> tuple[list[str], list[dict[str, Any]]]:
    script = read_upstream(f"{number}.js")
    match = _EXPECTED.search(script)
    assert match, script
    headers = read_upstream(f"{number}.js.sub.headers")
    fields = [
        line.split(":", 1)[1].strip(" \t")
        for line in headers.splitlines()
        if line.lower().startswith("server-timing:")
    ]
    return fields, json.loads(match.group(1))


def test_the_corpus_has_every_case() -> None:
    assert [str(n) for n in range(85)] == CASES


@pytest.mark.parametrize("number", CASES)
def test_wpt_parsing_case(number: str) -> None:
    fields, expected = _case(number)
    got = [(m.name, m.duration, m.description) for m in parse(fields)]
    want = [(e["name"], e.get("dur", 0), e.get("desc", "")) for e in expected]
    assert got == want

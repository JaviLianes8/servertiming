"""Every URL in the README, the guide and the project metadata answers.

The checks that need the network run only with TIMINGHEADER_LINKS=1, before a release;
the URL extraction itself is checked on every run.
"""

from __future__ import annotations

import os
import re
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/JaviLianes8/timingheader"
BLOB = f"{REPOSITORY}/blob/main/"

needs_network = pytest.mark.skipif(
    os.environ.get("TIMINGHEADER_LINKS") != "1", reason="set TIMINGHEADER_LINKS=1 to check links"
)


def _extract(text: str) -> set[str]:
    # A URL that ends a sentence or a clause is followed by punctuation that is not part of it.
    return {url.rstrip(".,;:!?'") for url in re.findall(r"https?://[^\s)\"<>`]+", text)}


def _urls() -> list[str]:
    found: set[str] = set()
    for name in ("README.md", "GUIDE.md", "CHANGELOG.md", "pyproject.toml"):
        found.update(_extract((ROOT / name).read_text(encoding="utf-8")))
    return sorted(found)


def test_sentence_punctuation_after_a_url_is_not_part_of_it() -> None:
    text = (
        "See https://a.example/x. Or https://b.example/y, https://c.example/z; https://d.example:"
    )
    assert _extract(text) == {
        "https://a.example/x",
        "https://b.example/y",
        "https://c.example/z",
        "https://d.example",
    }


def test_no_checked_url_ends_in_punctuation() -> None:
    assert [url for url in _urls() if url[-1] in ".,;:!?'"] == []


def _status(url: str) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        return error.code


@needs_network
def test_the_project_urls_point_at_the_repository() -> None:
    assert REPOSITORY in _urls()


@needs_network
@pytest.mark.parametrize("url", _urls())
def test_every_url_answers(url: str) -> None:
    if url.startswith(BLOB):
        # Files of this branch reach main when it merges: they must exist here, and the
        # repository must answer.
        path = url.removeprefix(BLOB).split("#", 1)[0]
        assert (ROOT / path).is_file(), path
        url = REPOSITORY
    status = _status(url)
    if "linkedin.com" in url:
        # LinkedIn answers every automated client with its own status 999.
        assert status in (200, 999), status
    else:
        assert status == 200, status

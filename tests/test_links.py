"""Every URL in the README, the guide and the project metadata answers.

Needs the network, so it runs only with TIMINGHEADER_LINKS=1, before a release.
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

pytestmark = pytest.mark.skipif(
    os.environ.get("TIMINGHEADER_LINKS") != "1", reason="set TIMINGHEADER_LINKS=1 to check links"
)


def _urls() -> list[str]:
    found: set[str] = set()
    for name in ("README.md", "GUIDE.md", "CHANGELOG.md", "pyproject.toml"):
        text = (ROOT / name).read_text(encoding="utf-8")
        found.update(re.findall(r"https?://[^\s)\"<>`]+", text))
    return sorted(found)


def _status(url: str) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return int(response.status)
    except urllib.error.HTTPError as error:
        return error.code


def test_the_project_urls_point_at_the_repository() -> None:
    assert REPOSITORY in _urls()


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

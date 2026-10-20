from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

import pytest

UPSTREAM = Path(__file__).resolve().parent / "upstream"


def upstream_manifest() -> dict[str, Any]:
    result: dict[str, Any] = json.loads((UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8"))
    return result


def _checked(path: Path, entry: dict[str, Any]) -> bytes:
    if not path.is_file():
        pytest.skip(f"{path.name} is not fetched; run python scripts/fetch_upstream.py")
    body = path.read_bytes()
    assert hashlib.sha256(body).hexdigest() == entry["sha256"], f"{path.name} differs from MANIFEST"
    return body


def read_upstream(name: str) -> str:
    """Return one fetched web-platform-tests file, checked against its manifest entry.

    The files are not committed: `python scripts/fetch_upstream.py` fetches them. Their
    tests skip while a file is absent and fail if it differs from the manifest.
    """
    manifest = upstream_manifest()
    path = UPSTREAM / manifest["folder"] / name
    return _checked(path, manifest["files"][name]).decode("utf-8")


def upstream_document(name: str) -> str:
    """Return one fetched specification as text, checked against its manifest entry."""
    manifest = upstream_manifest()
    path = UPSTREAM / manifest["documents_folder"] / name
    return _checked(path, manifest["documents"][name]).decode("utf-8")


def prose(markup: str) -> str:
    """Markup as plain text: tags removed, entities decoded, whitespace collapsed."""
    text = re.sub(r"<!--.*?-->", " ", markup, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()

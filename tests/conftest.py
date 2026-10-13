from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

UPSTREAM = Path(__file__).resolve().parent / "upstream"


def upstream_manifest() -> dict[str, Any]:
    result: dict[str, Any] = json.loads((UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8"))
    return result


def read_upstream(name: str) -> str:
    """Return one fetched third-party file, checked against its manifest entry.

    The files are not committed: `python scripts/fetch_upstream.py` fetches them. Their
    tests skip while a file is absent and fail if it differs from the manifest.
    """
    manifest = upstream_manifest()
    path: Path = UPSTREAM / manifest["folder"] / name
    if not path.is_file():
        pytest.skip(f"{name} is not fetched; run python scripts/fetch_upstream.py")
    body = path.read_bytes()
    entry = manifest["files"][name]
    assert hashlib.sha256(body).hexdigest() == entry["sha256"], f"{name} differs from MANIFEST"
    return body.decode("utf-8")

"""Fetch the third-party files listed in tests/upstream/MANIFEST.json.

The files (the web-platform-tests parsing corpus and the specifications the tests read
their rules and examples from) are not part of the repository. Their tests skip until
this script has fetched them; each download is checked against the size and sha256 in
the manifest, and every URL names a fixed revision.

    python scripts/fetch_upstream.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

UPSTREAM = Path(__file__).resolve().parents[1] / "tests" / "upstream"


def _fetch(url: str, entry: dict[str, object], target: Path) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": "timingheader-tests"})
    with urllib.request.urlopen(request, timeout=120) as response:
        body = response.read()
    digest = hashlib.sha256(body).hexdigest()
    if len(body) != entry["size"] or digest != entry["sha256"]:
        print(f"{target.name}: got {len(body)} bytes, sha256 {digest}; manifest differs")
        return False
    target.write_bytes(body)
    return True


def main() -> int:
    manifest = json.loads((UPSTREAM / "MANIFEST.json").read_text(encoding="utf-8"))
    jobs: list[tuple[str, dict[str, object], Path]] = []
    corpus = UPSTREAM / manifest["folder"]
    for name, entry in manifest["files"].items():
        jobs.append((manifest["base_url"] + name, entry, corpus / name))
    documents = UPSTREAM / manifest["documents_folder"]
    for name, entry in manifest["documents"].items():
        jobs.append((entry["url"], entry, documents / name))
    corpus.mkdir(parents=True, exist_ok=True)
    documents.mkdir(parents=True, exist_ok=True)
    failed = sum(not _fetch(url, entry, target) for url, entry, target in jobs)
    print(f"{len(jobs) - failed} files ok, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

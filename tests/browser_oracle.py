"""Ask real browser engines what they expose for Server-Timing response headers.

A local HTTP server answers ``/h?i=<n>`` with the field values of case ``n`` as separate
``Server-Timing`` response headers. A page fetches every case and reads
``performance.getEntriesByName(url)[0].serverTiming``; the result for each case is the
list of ``(name, duration, description)`` the engine exposes. Chrome, Edge, Chromium and
WebKit are driven by Playwright; the installed Firefox runs headless with a throwaway
profile and posts its results back to the server.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

View = list[tuple[str, float, str]]
FIREFOX = os.environ.get("TIMINGHEADER_FIREFOX", r"C:\Program Files\Mozilla Firefox\firefox.exe")

# Durations travel as strings when JSON cannot hold them: -0 and the infinities.
_READ = """async function readCases(start, count) {
  performance.clearResourceTimings();
  performance.setResourceTimingBufferSize(count + 10);
  const urls = [];
  for (let i = start; i < start + count; i++) {
    const url = new URL(`/h?i=${i}`, location.href).href;
    const response = await fetch(url, {cache: "no-store"});
    await response.arrayBuffer();
    urls.push([i, url]);
  }
  const code = (d) => Object.is(d, -0) ? "-0" : (Number.isFinite(d) ? d : String(d));
  const out = {};
  for (const [i, url] of urls) {
    let entries = performance.getEntriesByName(url);
    for (let wait = 0; entries.length === 0 && wait < 200; wait++) {
      await new Promise((done) => setTimeout(done, 10));
      entries = performance.getEntriesByName(url);
    }
    out[i] = entries.length ? entries[0].serverTiming.map(
      (s) => [s.name, code(s.duration), s.description]) : null;
  }
  return out;
}"""
_RUN = f"""<!doctype html><title>oracle</title><script>{_READ}
(async () => {{
  const total = Number(new URLSearchParams(location.search).get("n"));
  const all = {{}};
  for (let start = 0; start < total; start += 400) {{
    Object.assign(all, await readCases(start, Math.min(400, total - start)));
  }}
  await fetch("/result", {{method: "POST", body: JSON.stringify(all)}});
}})();</script>"""


def _server(cases: list[list[str]], results: list[str]) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            url = urlparse(self.path)
            self.send_response(200)
            if url.path == "/h":
                for field in cases[int(parse_qs(url.query)["i"][0])]:
                    self.send_header("Server-Timing", field)
            body = _RUN.encode() if url.path == "/run" else b"<!doctype html><title>o</title>"
            self._finish(body if url.path != "/h" else b"")

        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            results.append(self.rfile.read(length).decode("utf-8"))
            self.send_response(200)
            self._finish(b"")

        def _finish(self, body: bytes) -> None:
            self.send_header("Content-Type", "text/html")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: Any) -> None:
            pass

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


def _decode(rows: list[list[Any]] | None) -> View | None:
    return None if rows is None else [(n, float(d), s) for n, d, s in rows]


def _playwright(engine: str, base: str, count: int) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        if engine in ("chrome", "msedge"):
            # The installed Google Chrome or Microsoft Edge, driven over CDP.
            browser = playwright.chromium.launch(channel=engine)
        else:
            browser = getattr(playwright, engine).launch()
        try:
            page = browser.new_page()
            page.goto(base + "/")
            got: dict[str, Any] = {}
            for start in range(0, count, 400):
                script = f"({_READ})({start}, {min(400, count - start)})"
                got.update(page.evaluate(script))
            return got
        finally:
            browser.close()


def _firefox(base: str, results: list[str], count: int) -> dict[str, Any]:
    scratch = os.environ.get("TIMINGHEADER_SCRATCH")
    with tempfile.TemporaryDirectory(dir=scratch, ignore_cleanup_errors=True) as profile:
        args = [FIREFOX, "-headless", "-no-remote", "-profile", profile, f"{base}/run?n={count}"]
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(600):
                if results:
                    break
                threading.Event().wait(0.5)
        finally:
            # Firefox starts child processes; end the whole tree this call started.
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/T", "/F", "/PID", str(process.pid)], capture_output=True
                )
            process.kill()
            process.wait()
            threading.Event().wait(2)
    assert results, "Firefox posted no result"
    loaded: dict[str, Any] = json.loads(results[0])
    return loaded


def browser_views(cases: list[list[str]], engine: str) -> list[View | None]:
    """What ``engine`` exposes for each case, in order.

    ``engine`` is "chrome" or "msedge" (the installed browser), "firefox" (the installed
    Firefox, headless) or a Playwright engine ("chromium", "webkit").
    """
    results: list[str] = []
    server = _server(cases, results)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        if engine == "firefox":
            got = _firefox(base, results, len(cases))
        else:
            got = _playwright(engine, base, len(cases))
    finally:
        server.shutdown()
        server.server_close()
    return [_decode(got.get(str(index))) for index in range(len(cases))]

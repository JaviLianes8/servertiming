# servertiming improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Pin the ground truth: W3C Server Timing, RFC 9110, HTML number parsing, Fetch, WPT
- [x] Browser-compatible parser that passes the WPT corpus, multiple fields and trailers
- [x] Strict parser for the ABNF with error positions
- [x] Safe builder: no header injection, escaping, extension parameters, precision
- [x] Timing helpers: monotonic clock, context manager and decorator (sync and async), timers
- [x] Command line checker
- [x] Contracts: WPT corpus (local), cited spec vectors, round trip, README examples, typing
- [x] Docs and packaging: README, CHANGELOG, metadata, installed-wheel e2e test
- [ ] Gates: ruff format, ruff check, mypy --strict, pytest
- [ ] Mutation run: removing guarded logic makes the suite fail
- [ ] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

## Starting point

`0.1.0` gives `Metric`, `build`, `parse` and a `Timing` collector. Compared with the sources
below:

- `parse` splits on `;` and `=` and keeps whatever lies between, so it disagrees with what
  browsers expose in many places: `metric;desc=d1 d2` gives `d1 d2` (browsers: `d1`),
  `metric==""foo;dur=1` gives the name `metric==""foo` (browsers: `metric`), `[` becomes a
  metric (browsers: nothing), a repeated `dur` keeps the last value (the spec keeps the
  first), parameter names with mixed case are matched only by luck of `.lower()`, and an
  unterminated quoted string comes back raw.
- Duration parsing uses Python `float()`, which reads `1_000` as 1000 (HTML: 1) and
  rejects `12ms` or `1.5.2` (HTML: 12 and 1.5).
- Several header fields (repeated `Server-Timing` lines, a trailer) cannot be passed
  together, and extension parameters are thrown away.
- `build` checks the name but writes any description inside quotes: a description holding
  CR or LF splits the response header (header injection), and characters no HTTP field can
  carry are written as is.
- There is no strict mode to validate a header against the grammar before sending it.
- `Timing` checks names only when the header is rendered, at the end of the request, far
  from the bug. `measure` cannot decorate a function, and there is no start/stop timer for
  work that does not fit in one block.

## Sources (fetched 2026-10-13)

- W3C Server Timing, Editor's Draft, https://w3c.github.io/server-timing/ (repository
  w3c/server-timing at commit 573ee35b45bd26d4a88747b97b0db9f6d9963038): section 2, the
  ABNF, first parameter wins, extraneous characters ignored, the parse algorithm; sections
  3.2 and 3.3 for the duration and description getters; the trailer example in section 6.
- RFC 9110, https://www.rfc-editor.org/rfc/rfc9110.txt: 5.5 field values, 5.6.1 lists
  (sender and recipient rules), 5.6.2 tokens, 5.6.3 whitespace, 5.6.4 quoted strings.
- WHATWG HTML, https://html.spec.whatwg.org/multipage/common-microsyntaxes.html (commit
  86190a4d7c155a668ae547d2b207916ed4643084): 2.3.4.3, valid floating-point number and the
  rules for parsing floating-point number values (used by the duration getter).
- WHATWG Fetch, https://fetch.spec.whatwg.org/ (commit
  e9460d1b22ead1c6a72eeac37fb2ec0dc01aeb1d): collect an HTTP quoted string; get, decode,
  and split (repeated fields are joined with a comma before parsing).
- web-platform-tests at commit 1b67fafba1d46d158b45a831bb604d86c9b5c5a8:
  `server-timing/server_timing_header-parsing.https.html` and the 85 pairs
  `server-timing/resources/parsing/<n>.js` (expected metrics) and `<n>.js.sub.headers`
  (the header sent), BSD-3-Clause. Not committed: `tests/upstream/MANIFEST.json` records
  URL, revision, size, sha256 and licence for each file, `scripts/fetch_upstream.py`
  fetches and checks them into the ignored `tests/upstream/` folder, and their tests skip
  while they are absent.

Where the sources disagree: the parse algorithm block in the spec collects everything up
to `;` as the name or value, while the normative prose above it says extraneous characters
after a name or a value are ignored and the WPT corpus (what browsers ship) expects
`metric;desc=d1 d2` to give `d1` and `[` to give no metric. WPT also reads a quoted string
that never closes as empty, where Fetch would keep its text. The lenient parser follows the
WPT corpus and the prose; the differences are listed in the README.

## Ranked improvements

1. **Browser-compatible parser.** One tokenizer over the joined field values: a metric
   name is a token, extraneous characters after a name or a value are skipped up to the
   next `;` or `,` (quoted strings inside them are skipped whole), parameter names are
   case-insensitive, the first occurrence wins even when empty or invalid, `dur` and `desc`
   values may be a token or a quoted string. Passes all 85 WPT cases.
2. **Durations read like a browser.** The HTML rules for parsing floating-point numbers,
   step by step: leading whitespace, `+` ignored, `.5`, `1.`, trailing junk ignored,
   correct rounding, `-0` becomes `0`, overflow is an error. `Metric.duration` and
   `Metric.description` give the values a browser exposes (`0` and `""` when absent).
3. **Safe builder.** A description is a token or a quoted string with `"` and `\`
   escaped; anything a quoted string cannot hold (controls other than tab, DEL, anything
   above U+00FF) raises `ServerTimingError`, so no input can split a header. Durations must
   be finite real numbers (not `bool`), with an optional `precision` to keep headers short.
   Extension parameters are written and checked the same way.
4. **Strict parser.** `parse(value, strict=True)` follows the ABNF with the RFC 9110
   recipient list rule, rejects a repeated parameter name and a `dur` that is not a valid
   floating-point number, and raises `ServerTimingError` with the field index and position.
5. **Several fields and trailers.** `parse` takes one string or an iterable of field
   values (headers followed by trailers), joined as Fetch does.
6. **Typed metric value.** `Metric` keeps extension parameters (`params`, `param()`), and
   `str(metric)` serializes one metric.
7. **Timing helpers.** Names and descriptions are checked when recorded; `measure` works
   as a context manager and as a decorator for plain and `async` functions (the time spent
   awaiting is counted, not just the coroutine creation); `start()` returns a `Timer` for
   work spread over callbacks; the default clock is `time.perf_counter` (monotonic).
8. **Command line checker.** `servertiming 'db;dur=53'` (or lines on stdin, as copied from
   `curl -i`) prints the metrics and exits non-zero when the value breaks the grammar.
9. **Contracts.** WPT corpus as a local test, cited spec examples, a seeded round trip
   (`parse(build(m), strict=True) == m`), README examples executed, typing checked with
   mypy, installed-wheel end-to-end test, mutation run.
10. **Packaging.** Classifiers, keywords, console script, sdist without the fetched files.

Deferred: splitting a long header into several fields under a size limit (no ground truth
to check it against, and servers differ in their limits).

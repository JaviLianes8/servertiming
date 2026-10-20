# timingheader 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to timingheader, developed as
`servertiming` up to 0.2.0. Nothing was ever on PyPI under either name (PyPI refused the
old name at upload as too similar to an existing project), so there is no release to
upgrade from; every change against 0.2.0 is still listed in the CHANGELOG.

Progress:
- [x] Branch `release/1.0.0` created from `main` (acceacf, 0.2.0)
- [x] New name chosen and applied (distribution, package, command, URLs)
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: specifications fetched live, real browsers as oracles (item 7)
- [x] Contract, fuzz and hostile input (items 6, 9)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e, every Python (items 8, 10, 13, 14)
- [x] Author mutation round (item 18)
- [x] Gates (item 15)
- [x] PR and trace guard (merge and publish, item 17, are the maintainer's)
- [x] Project links moved to the new repository name (ae28650)
- [ ] Five QA lenses (item 19): round 1 fixed in 45e91a9; round 2 (11 findings) fixed in 921ccf5 and 87f8cae; round 3 (b, d PASS; c one low finding, fixed in ae28650; a, e did not report); round 4 (a, b, c, e on 308bf7c, 13 findings) fixed in 065be67; re-verification pending
- [ ] Independent reviewer (item 16, run after this stage)

## Scorecard

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: seven names kept from 0.2.0, signatures pinned by `tests/test_contract_api.py`; every change in CHANGELOG and GUIDE |
| 2 | `__all__` exact, no private imports in docs | PASS |
| 3 | Docstrings with runnable examples, doctests | PASS: 18 doctests (every public function, method and property); README (9 outputs) and GUIDE (11) examples run as tests, and type-check under `mypy --strict` as consumer code |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed`, typing checked from a consumer snippet, also against the installed wheel |
| 5 | Typed, documented, bounded errors | PASS: `ServerTimingError` (a `ValueError`) with `position` and `field`, `TypeError` for wrong types, messages quote at most 60 characters |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: W3C, RFC 9110, HTML and Fetch fetched at fixed revisions, WPT corpus, Chrome 155, Firefox 158 and WebKit driven over HTTP |
| 8 | Real e2e from the wheel | PASS: built wheel installed in a throwaway venv, used from an empty folder, command driven by subprocess; no PyPI release to upgrade from |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t (all again at ae28650); 3.8.20 and 3.9.25 refused by `requires-python` |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links, badge |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-20 (the date of the 1.0.0 commits; the maintainer re-dates it if the release is published later); 0.2.0 and 0.1.0 dated from their commits |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates (last at ae28650) |
| 16 | Independent reviewer | pending (next stage) |
| 17 | PR and trace guard | PR from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: author round of 30 mutants, all killed (one after a contract was added); M26 again and M31, M32 at ae28650, killed |
| 19 | Five independent QA lenses | round 1: 21 findings, round 2: 11 findings, round 3: 1 finding, round 4: 13 findings, all fixed (see QA lenses); re-verification pending |

## Name

PyPI refused `servertiming`. The new name `timingheader` was checked on 2026-10-20:
`https://pypi.org/pypi/<name>/json` answers 404 for `timingheader`, `timing-header`,
`timing_header`, `timing.header`, `timingheaders`, `timing-headers`, `timing_headers`,
`timing.headers`, `tlmlngheader`, `t1m1ngheader` and `tImIngheader`, and
`pypi.org/simple/timingheader/` is 404. The distribution, the import package, the
command, the tests, the docs and the project URLs use it; the old name appears in one
CHANGELOG line. The project URLs and the README links point at
https://github.com/JaviLianes8/timingheader (changed from the old repository URL in
ae28650): the GitHub repository and the local folder keep the old name until the merge,
where the maintainer renames them, so that URL answers 404 until then and
`tests/test_links.py` is to be run after the rename (every other URL, and every linked file
of this branch, is checked as before). Rechecked on 2026-10-20: `timingheader`,
`timing-header`, `timing_header`, `timing.header` and `timingheaders` still answer 404 on PyPI.

## Defects found in 0.2.0

Reproduced before changing anything:

- `build([Metric("db", dur=10**5000)])` raised a bare `ValueError` from `repr` (the int
  digit limit), and `precision=10**20` a bare `ValueError` from the formatter.
- Error messages quoted the whole input: a 100,000 character name, metric or parameter
  came back whole (100 KB messages).
- `Metric("a").param(1)` raised `AttributeError`; a `Metric` with a list of parameters
  could not be hashed; `str.lower` turned a Kelvin sign in a parameter name into `k`, so
  a name that is not a token was written as one.
- `Timing.measure` decorated a generator function and recorded only the time to create
  the generator.
- The command joined folded header lines by repeated string concatenation (quadratic).
- `build` raised `ServerTimingError` (a `ValueError`) for arguments of the wrong type.
- No public docstring had a runnable example; the README linked LICENSE relatively; the
  README claimed the parser reads "the way browsers do" without having asked a browser.

## API review (item 1)

Kept: the seven public names of 0.2.0 with their signatures, parameter names and
defaults. Changed, all in the CHANGELOG and GUIDE: `TypeError` for arguments of the wrong
type in `build`, `str(metric)`, `Timing` and `Metric.param`; `precision` limited to 0 to
20; ASCII-only lowering of parameter names; a list of parameters stored as a tuple;
`Timing.measure` refuses generator functions and non-callables, `Timing` a non-callable
clock; bounded error messages; public classes report `timingheader` as their module
(pickles never name a private module). Internal: `Measure` and `Timer` moved to
`_measure.py` so every file stays under 200 lines with the examples.

## Ground truth (item 7)

Fetched on 2026-10-20 by `scripts/fetch_upstream.py` into the ignored `tests/upstream`
folder; `tests/upstream/MANIFEST.json` records URL, revision, size, sha256 and licence,
and the tests check the hash before reading. Nothing fetched is committed or shipped.

- W3C Server Timing, Bikeshed source at commit 573ee35 (`tests/test_spec_w3c.py`): the
  ABNF is cut from the text and compared with what strict mode implements; the example
  headers, the trailer and the table of the seven metrics they carry are cut from the
  text and parsed in both modes; the first-instance, extraneous-characters, unknown
  parameter and getter rules are located and exercised.
- RFC 9110 (`tests/test_spec_rfc9110.py`): `tchar`, `qdtext`, `quoted-pair` and `OWS` are
  parsed out of the ABNF and compared with strict parsing and with `build` code point by
  code point (U+0000 to U+02FF, a surrogate, an astral character); the sender and
  recipient list rules are located and exercised.
- WHATWG HTML source at commit c97dc91 (`tests/test_spec_html.py`): the definition of a
  valid floating-point number and the rules for parsing floating-point number values are
  located; an independent step-by-step transcription in exact rational arithmetic agrees
  with the library on every string of up to five characters over the characters the
  steps look at (271,453 strings) and on 60,000 seeded longer ones.
- WHATWG Fetch commit snapshot 59afe34: the `, ` join of repeated fields.
- web-platform-tests corpus, 85 cases at commit 1b67faf (unchanged upstream since 2018),
  fetched again with the same sha256: all pass.
- Real browsers (`tests/test_browsers.py`, `TIMINGHEADER_BROWSERS=1`): a local server sends
  each case as real response headers and a page reads `serverTiming` back. Google Chrome
  155.0.8059.84 and Firefox 158.0 (installed) and the WebKit of Playwright 1.64. On 3,000
  generated headers that follow the grammar each engine exposes exactly what `parse`
  gives; Chrome and Firefox read all 85 corpus cases as `parse` does, WebKit misreads two.
  On malformed text the engines disagree with one another; the measured differences are
  pinned in the test and listed in the GUIDE, and the README no longer claims more than
  was measured. All 12 browser tests pass (run on this PC, 91 s).

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`: three seeds, 20,000 hostile and near-valid strings each through the
lenient parser (never raises, names are tokens, durations finite, parameters unique and
lower case), strict mode accepting exactly a regular expression written from the grammar
plus the sender rules, 10,000 per seed rebuilt and read back, 4,000 random metrics built
or refused with short messages, 2,000 header blocks through the command reader.
`tests/test_hostile.py`: sixteen input shapes timed at 50,000 and 200,000 characters
through both parsers (linear), 200,000 folded lines through the command, 1 MB values in
every error path, ints of 100,000 digits, objects whose `repr` raises.

## Author mutation round (item 18)

30 mutants over every module, each applied alone to a fresh clone of the pushed branch
(fetched sources present), the full suite run with `-x` and a 300 s per-test limit, on
this PC under a machine turn. 29 were killed at once. M30 survived: no contract pinned
how a huge int is described. `test_a_huge_int_is_described_by_its_size_not_written_out`
was added in 8d2adff and fails under M30.

| Mutant | Module | Change | Killed by |
| --- | --- | --- | --- |
| M01 | `_syntax.py` | tchar drops the backtick | `test_fuzz.py::test_strict_mode_accepts_exactly_the_grammar[11]` |
| M02 | `_syntax.py` | obs-text lower bound off by one | `test_fuzz.py::test_strict_mode_accepts_exactly_the_grammar[11]` |
| M03 | `_syntax.py` | quote stops escaping backslashes | `test_build.py::test_description_quotes_and_backslashes_are_escaped` |
| M04 | `_syntax.py` | ASCII lowering becomes `str.lower` | `test_contract_api.py::test_invalid_values_raise_server_timing_error[<lambda>8]` |
| M05 | `_parse.py` | last occurrence of a parameter wins | doctest `timingheader.parse` |
| M06 | `_parse.py` | unterminated quoted string keeps its text | `test_parse.py::test_an_unterminated_quoted_string_reads_as_empty` |
| M07 | `_parse.py` | skipping does not jump over quoted strings | `test_parse.py::test_extraneous_characters_after_a_name_are_ignored` |
| M08 | `_parse.py` | lenient parameter names keep their case | doctest `timingheader.parse` |
| M09 | `_strict.py` | strict accepts a repeated parameter | `test_docs.py::test_every_example_runs_and_prints_its_comments[GUIDE-5-11]` |
| M10 | `_strict.py` | strict accepts a trailing comma | `test_spec_rfc9110.py::test_the_list_rule_for_senders_and_recipients` |
| M11 | `_strict.py` | error position off by one | doctest `timingheader.ServerTimingError` |
| M12 | `_strict.py` | strict accepts any `dur` | doctest `timingheader.ServerTimingError` |
| M13 | `_number.py` | negative zero kept | `test_docs.py::test_every_example_runs_and_prints_its_comments[GUIDE-5-11]` |
| M14 | `_number.py` | a leading plus is an error | `test_docs.py::test_every_example_runs_and_prints_its_comments[GUIDE-5-11]` |
| M15 | `_number.py` | overflow is not an error | `test_docs.py::test_every_example_runs_and_prints_its_comments[GUIDE-5-11]` |
| M16 | `_number.py` | form feed is not whitespace | `test_number.py::test_parse_number_follows_the_html_rules` (leading whitespace case) |
| M17 | `_number.py` | precision keeps trailing zeros | `test_build.py::test_precision_rounds_durations[6-12.5678]` |
| M18 | `_build.py` | `dur` and `desc` accepted as extra parameters | `test_build.py::test_build_rejects_bad_extension_parameters[params1]` |
| M19 | `_build.py` | precision upper bound off by one | `test_build.py::test_build_rejects_a_precision_out_of_range[21]` |
| M20 | `_build.py` | a `str` is iterated as metrics | `test_build.py::test_build_rejects_something_that_is_not_a_metric` |
| M21 | `_metric.py` | an int duration stays an int | doctest `timingheader.Metric` |
| M22 | `_metric.py` | parameter lookup is case sensitive | doctest `timingheader.Metric.param` |
| M23 | `_metric.py` | a list of parameters stays a list | doctest `timingheader.Metric` |
| M24 | `_measure.py` | async functions timed only until the coroutine is made | `test_collector.py::test_measure_decorates_a_coroutine_function_and_times_the_await` |
| M25 | `_measure.py` | async generator functions accepted | `test_contract_api.py::test_wrong_argument_types_raise_type_error[<lambda>23]` |
| M26 | `_collector.py` | durations in the wrong unit | doctest `timingheader.Measure` |
| M27 | `_cli.py` | invalid values exit with 0 | `test_cli.py::test_invalid_input_is_reported_and_exits_one` |
| M28 | `_cli.py` | folded lines dropped | `test_hostile.py::test_the_command_reads_many_folded_lines_in_linear_time` |
| M29 | `_errors.py` | error excerpts not cut | `test_hostile.py::test_error_messages_stay_short_for_huge_values[<lambda>0]` |
| M30 | `_errors.py` | huge int reprs not avoided below 10**5000 | `test_hostile.py::test_a_huge_int_is_described_by_its_size_not_written_out` (added) |

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

- Wheel: the package modules, `py.typed`, `__main__.py`, METADATA, `entry_points.txt`
  (`timingheader = timingheader._cli:main`) and `licenses/LICENSE`; no tests or scratch
  files. Metadata: version 1.0.0, `License-Expression: MIT`, `Requires-Python: >=3.10`,
  Production/Stable, Homepage, Source, Issues and Changelog URLs, no runtime dependency.
- sdist: sources, tests, `tests/upstream/MANIFEST.json`, scripts, README, GUIDE,
  CHANGELOG, CONTRIBUTING, LICENSE; none of the fetched third-party files, the
  improvement notes or this report. `twine check --strict` passes on both.
- `tests/test_e2e_wheel.py` (`TIMINGHEADER_E2E=1`) builds both, inspects them, installs
  the wheel in a fresh venv, drives it from an empty folder with `-I`, and runs the
  installed command (table, JSON, response headers on stdin, exit codes 0, 1 and 2) and
  `python -m timingheader`.
- Every interpreter on this PC from `requires-python` up, at bd6405c (and the typing
  test again at ed535e1 on 3.14.2t): the wheel installed in a fresh venv, the sdist's
  own suite run with `src` removed and the fetched files present, and the installed
  package's doctests. CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2
  free-threaded: 476 passed, 13 skipped (the browser and e2e tests, which run
  separately), 16 doctests passed each. 3.8.20 and 3.9.25 refuse the install.

## Gates (item 15)

At 8d2adff from a fresh clone on this PC, each command on its own, with the fetched files
and `TIMINGHEADER_E2E=1`: `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests` and `pytest` (494 passed, 12 skipped: the browser tests, run
separately above) all exit 0.

## QA lenses (item 19)

### Round 1

Five independent lenses (a: API and docs, b: correctness and ground truth, c: adversarial,
d: packaging and e2e, e: contract strength) reviewed 17c7c9b. Every finding was accepted
and fixed in 45e91a9; none is disputed. Each behaviour fix has a contract test that failed
on 17c7c9b before the fix (`tests/test_qa_recording.py`, `tests/test_qa_cli.py`), and every
behaviour change is in the CHANGELOG.

| Lens | Id | Finding | Fix |
| --- | --- | --- | --- |
| a, c | A1, C-F2 | Every `Measure` made its own context variable; a long-lived thread kept one per request (100,000 requests: 100,000 variables, about 11.8 MB) | One module-level context variable holds the running blocks; the same repro now leaves 1 variable and 0 KiB. Contracts: no growth in a long-lived context or a worker thread, a finished `Measure` is freed |
| a, d | A2, D-F2 | Project URLs and README links pointed at a repository that does not exist (404) | They point at `JaviLianes8/servertiming`; `tests/test_links.py` (`TIMINGHEADER_LINKS=1`) checks every URL in README, GUIDE, CHANGELOG and pyproject: 20 passed on 2026-10-20 (LinkedIn answers bots with 999, accepted; files of this branch checked in the tree until it merges) |
| a | A3 | `build` docstring said "a real number" for the duration | Says an `int` or a `float`, not a `bool` |
| a | A4 | `field_list`, `parse_lenient`, `parse_strict`, `Iterable`, `annotations` reachable as public names | Imported under private names or only for type checking; contract: `dir(timingheader)` minus underscores equals `__all__` |
| a, d | A5, D-F5 | `build` and the property getters reported private modules; `pickle.dumps(build)` named `timingheader._build` | Relabelled; contract: every public name and every member and property accessor of the public classes report `timingheader`, `build` and `parse` pickle by the package name |
| a | A6 | `Measure` and `Timer` constructors checked nothing | They check `timing`, name, description (and `start`) as `Timing.measure` and `Timing.start` do |
| b | B-F1 | Docs said `parse` is "the W3C algorithm" and "follows the spec", but the Editor's Draft algorithm differs from the corpus | README, GUIDE and docstrings say `parse` follows the web-platform-tests corpus; a new GUIDE section lists the differences. `tests/test_spec_w3c_algorithm.py` transcribes the algorithm from the fetched text, checks the steps are still there, pins the listed differences and measures 35 of 85 corpus cases on which algorithm and corpus disagree (the reviewer's count, reproduced independently) |
| b | B-F2 | The command merged the fields of every response in a dump with redirects | A status line starts a new response; only the last one is read |
| c | C-F1 | A `str` subclass could hide CR/LF from the checks and reach the header | Every check and write works on a plain `str` copy; `parse` input too |
| c | C-F3 | A clock giving NaN or infinity recorded a metric that broke every later `header()` | `ServerTimingError` where the measurement ends, nothing recorded |
| c | C-F4 | Exit without a matching enter raised an internal `ValueError` | `RuntimeError` with a clear message, documented |
| d | D-F1 | `--json` wrote invalid JSON when stdout could not encode a character | `ensure_ascii=True`; tested with cp1252, ASCII and UTF-8 stdout |
| d | D-F3 | `BrokenPipeError` traceback when the reader closed early | Output stops quietly, the exit status still reflects validity; subprocess test |
| d | D-F4 | `mypy --strict src tests` red without playwright | mypy override for `playwright`; checked in a fresh venv without it (red before, green after) |
| e | E-F1 | Exit 2 for blank arguments not pinned (M70) | Pinned; invalid values are now numbered by their place among the arguments, blank ones included |
| e | E-F2 | ISO-8859-1 stdin not pinned (M86) | Subprocess test with a raw 0xE9 byte |
| e | E-F3 | Status-line detection not pinned (M76) | Test with a status line alone, exit 2 |
| e | E-F4 | JSON escaping not pinned (M68) | Raw `--json` text pinned (now ASCII escapes, see D-F1) |

Mutants re-run against the new tests, one at a time on `_cli.py`: M70, M86, M76 and M68
as described by lens e, plus "every response kept" (B-F2) and "broken pipe re-raised"
(D-F3); all six killed.

Gates at 45e91a9, on Elena's PC (CPython 3.14.2, fresh venv, fetched files present,
`TIMINGHEADER_E2E=1`): `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests` exit 0; `pytest`: 538 passed, 33 skipped (browser tests and the
link check, which run on request) in 39 s.

### Round 2

The five lenses re-verified 45e91a9 (pushed head ddd4e84). Every round 1 finding was
confirmed fixed; the new findings below were all accepted and fixed in 921ccf5, with the
`parse` part of D-N1 reworked in 87f8cae so its pinned signature stays the same. None is
disputed. Each behaviour fix has a contract test that failed on ddd4e84 before the fix
(`tests/test_qa_contexts.py`, `tests/test_qa_cli_output.py`), and every behaviour change
is in the CHANGELOG.

| Lens | Id | Finding | Fix |
| --- | --- | --- | --- |
| a, d | A-N1, D-N2 | Leaving a `Measure` block from a context copied after the enter (another asyncio task, `asyncio.to_thread`, `copy_context().run`, every new thread on free-threaded 3.14) succeeded, and the exit where the block began recorded the metric again; the suite was red on 3.14.2t | Each running entry records the thread and asyncio task that entered it and is used once: an exit from another thread or task raises `RuntimeError` and leaves the entry, and a second exit through a copy of the context raises `RuntimeError`; nothing is recorded twice. Contracts: `asyncio.create_task`, `asyncio.to_thread`, a thread running a copied context (what 3.14t does), a second exit through `copy_context().run`. Docstring, GUIDE and CHANGELOG say exactly this. The suite passes on 3.14.2t |
| b | B-F1b | README "Why" still said `parse` reads a header "as the specification says" | Now "as browsers and the web-platform-tests corpus do" |
| c | C-N1 | An `int` clock reading too large for a float raised `OverflowError` from `Timer.stop()` and `Measure.__exit__` | Treated as a duration that is not finite: `ServerTimingError`, nothing recorded, the timer keeps running. Contract with a huge start, a huge end and a huge negative end, for a timer and a block |
| c | C-N2 | With no stdout at all (fd 1 closed, `pythonw`) the command crashed with `AttributeError` and exit 1 | `_write` treats a missing stdout like a reader that stopped: the values are still checked and the exit status is theirs |
| d | D-N1 | `typing.get_type_hints` and `inspect.signature(eval_str=True)` raised `NameError` on `parse` (`Iterable`) and on the `Measure` and `Timer` constructors (`Timing`) | `Timing` is imported at run time by the module of `Measure` and `Timer` (the collector imports them after defining `Timing`); `parse` delegates to a private function whose module imports `Iterable`, and names it as `__wrapped__`, so the annotations resolve while `Iterable` stays out of the package and the pinned signature text is unchanged. Contract: every public function, method and property getter resolves with both calls |
| e | E-N1 | No test of a reader closed before a small write (mutants C07, C09, C10 survived) | Subprocess tests with the read end of a pipe closed before the command starts, for a valid value, `--json` and an invalid value: exit 0 or 1, no traceback |
| e | E-N2 | No test of two blocks left out of order (S08, S11 survived) | Interleaved exits by hand and through `ExitStack`, both durations asserted |
| e | E-N3 | Numbering of values read from stdin not pinned (C02) | Exact `invalid value 2` line for stdin values |
| e | E-N4 | Last-response rule pinned only for HTTP/1.1 then HTTP/2 (C05) | Two HTTP/1.1 responses, through `fields_from_lines` and through the command |
| e | E-N5 | `Timer` refusing a `bool` start not pinned (S04) | `True` case added to the constructor contract |
| e | E-N6 | The plain copy in `field_list` not pinned (X01) | Lenient and strict `parse` of a `str` subclass whose `__len__` and `__getitem__` lie, alone and in a list |

Mutants re-run one at a time against the new tests (laptop, CPython 3.14.6, fresh clone of
87f8cae, a clean baseline first): lens e's C07, C09, C10, C02, C05, S04, S08 and S11, plus
"no owner check", "entry usable twice", "OverflowError not caught", "stdout `None` not
handled" and "`parse` without `__wrapped__`"; all thirteen killed, each by the new test
meant for it.

Gates at 87f8cae on the laptop (CPython 3.14.6, fresh clone and venv, fetched files
present, `TIMINGHEADER_E2E=1`): `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` exit 0; `pytest`: 590 passed, 33 skipped
(browser tests and the link check, which run on request). Interpreter matrix at 87f8cae on
this PC (wheel installed in a fresh venv, the sdist's suite with `src` removed): CPython
3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2 and 3.14.2t all pass (572 or 573 passed, 34
skipped; 16 doctests each), and the wheel e2e passes; `twine check --strict` passes on
both artifacts.

### Round 3

The lenses re-checked 90c703f. Lens b (correctness) and lens d (packaging, e2e, every
Python) reported PASS with every round 2 finding confirmed fixed. Lens c confirmed its
round 2 findings fixed and reported one new low finding. Lenses a and e did not finish a
report; they are to be run again. Both PASS verdicts predate ae28650, which changes
`_collector.py`, so they are to be renewed on it.

| Lens | Id | Finding | Fix |
| --- | --- | --- | --- |
| c | N3 | The clock was called inside the guard that turns an `OverflowError` from a huge `int` reading into an infinite duration, so an `OverflowError` raised by the clock itself was reported as "the clock gave a duration that is not finite: inf", with the original exception lost | The clock is read before the guard; only the subtraction and the scaling are guarded, so an exception from the clock (an `OverflowError` included) reaches the caller as it is, and nothing is recorded. Contract `tests/test_qa_clock.py` (timer, block, decorated function; an `OverflowError` and another exception), red on 90c703f for the `OverflowError` cases. CHANGELOG and GUIDE say so |

Also in ae28650, at the maintainer's instruction for the rename: the project URLs, the
README links and their tests point at https://github.com/JaviLianes8/timingheader (see
Name), and the CHANGELOG names the old project in one line.

Mutants on `_collector.py`, one at a time on a copy of ae28650 (the suite with `-x`):
M26 rewritten for the new code ("durations in the wrong unit"), killed by the doctest of
`timingheader.Measure`; M31 "clock read inside the overflow guard" (the N3 code), killed by
`test_qa_clock.py::test_an_error_from_the_clock_reaches_the_caller_of_stop[error0]`; M32
"overflow from a huge int reading re-raised", killed by
`test_qa_contexts.py::test_a_clock_reading_too_large_for_a_float_raises_the_documented_error`.

Gates at ae28650 on Elena's PC under a machine turn (CPython 3.14.2, fresh clone of the
pushed branch and venv, fetched files present, `TIMINGHEADER_E2E=1`): `ruff format
--check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests` exit 0;
`pytest`: 595 passed, 33 skipped (browser tests and the link check, which run on request).
`twine check --strict` passes on the wheel and the sdist built from that clone.
Interpreter matrix at ae28650 on the same machine (each interpreter copied from this PC,
the wheel installed in a fresh venv, the sdist's suite with `src` removed and the fetched
files present, then the installed package's doctests): CPython 3.10.19, 3.11.5 and 3.12.12
577 passed, 3.13.2, 3.14.2 and 3.14.2t 578 passed (34 skipped each), 16 doctests each;
3.8.20 and 3.9.25 refuse the install (`requires-python >=3.10`).

### Round 4

Lenses a, b, c and e reviewed 308bf7c. Every finding was accepted and fixed in 065be67;
none is disputed. Each behaviour fix has a contract test that failed on 308bf7c before
the fix (`tests/test_qa_values.py`, `tests/test_qa_nesting.py`,
`tests/test_qa_doc_typing.py`), and every behaviour change is in the CHANGELOG.

| Lens | Id | Finding | Fix |
| --- | --- | --- | --- |
| a | F1 | `Metric.params` was typed as a tuple only, so the `Metric` docstring example with a list failed `mypy --strict` as consumer code | `Metric` has an explicit constructor whose `params` takes a tuple or a list of pairs; the field stays a tuple (the dataclass fields, defaults, equality, hashing and pickling are unchanged). Contract `test_qa_doc_typing.py`: every doctest and every README and GUIDE python block is type-checked as consumer code under `mypy --strict` (red on 308bf7c on the `Metric` example) |
| a | F2 | README and the `build` docstring said any control character is refused; tab is allowed | Both say "a control character other than tab" |
| a | F3 | The 0.2.0 section named the command `timingheader` | Restored to `servertiming`, the name it had at 0.2.0 |
| a | F4 | 1.0.0 dated 2026-10-19, older sections undated, bracketed versions without link definitions, `dir()` claim literally false | 1.0.0 dated 2026-10-20, 0.2.0 2026-10-13 and 0.1.0 2026-10-12 (their commits), brackets dropped; the claim now says the names without a leading underscore are exactly `__all__` (what the contract checks) |
| a | F5 | `Timer.stop` and `Timer.running` had no runnable example | Both have one. `Timer` moved to `_timer.py` so every file stays under 200 lines; it still reports `timingheader` as its module |
| a | N1, N2 | Notes, not counted | N1: the `timingheader` URLs are to be re-checked after the rename (`tests/test_links.py`), unchanged. N2: left as is; `Timer` takes `desc` before `start`, so a default for `desc` would only fit `Measure`, and the GUIDE documents both constructors |
| b | B1 | Durations were said to be written in the shortest form, but repr pads the exponent (`1e-05`, `1e+16`) | `format_number` writes the exponent without a plus sign or leading zeros (`1e-5`, `1e16`, `1.5e-7`); GUIDE and docstring say "the shortest digits that read back as the same double (Python's `repr`)". Contract: those values build to the short form and strict-parse back equal |
| c | F1 | Nested `Measure` blocks and blocks left open cost quadratic time (the running tuple was copied on every enter and exit) | The running entries are a persistent linked stack of `(entry, rest)` pairs: enter and the innermost exit are constant time, an out-of-order exit rebuilds only the entries above it. Contracts: 8 times the depth stays under 24 times the time (it was about 47 to 60), 40,000 open entries leave later blocks under 5 times slower (it was about 110), and an out-of-order exit with an entry left open still records both blocks |
| c | F2 | An `int` duration beyond the float range stayed an `int`: `repr` raised `ValueError`, `duration` returned an `int` | Stored as an infinity of its sign, as the docstring now says; `repr` and `duration` work and `build` refuses it with `ServerTimingError` |
| c | F3 | `Metric.param` raised `ValueError` or `AttributeError` for malformed `params` | `TypeError` ("params must hold (name, value) pairs"), documented |
| c | F4 | A `precision` that subclasses `int` could get around the 0 to 20 range check | `build` (and so `Timing.header`) works on `int.__index__(precision)`, a plain `int`, for the check and the format |
| c | F5 | `shown()` called `abs` and `bit_length` on the object, so an `int` subclass hook replaced the documented `TypeError` | `int.__abs__` and `int.bit_length` are called directly |
| e | F1 | No test of a header line folded with a tab (mutant N11 survived) | Subprocess test with a tab, a space and a space plus tab continuation, and a direct `fields_from_lines` case |
| e | F2 | The `TypeError` message for a non-`str` metric or parameter name was not pinned (N21 survived) | Exact messages pinned for `build`, a parameter name, `Timing.add` and `Timing.measure` |

Mutants re-run one at a time against the new tests on this PC: lens e's N11 (folding
only on a space) is killed by `test_qa_cli.py::test_a_line_folded_with_a_tab_or_a_space_continues_the_field`,
and N21 (`check_token` type guard removed) by
`test_qa_values.py::test_a_name_that_is_not_a_str_is_named_in_the_type_error`.

Gates at 065be67 on the laptop under a machine turn (CPython 3.14.6, a clone of the
branch, a fresh venv, fetched files present, `TIMINGHEADER_E2E=1`): `ruff format --check .`,
`ruff check .`, `mypy --strict src`, `mypy --strict src tests` exit 0; `pytest`: 626
passed, 33 skipped (browser tests and the link check, which run on request). The changed
areas (new contracts, API contract, typing, doctests) also pass on CPython 3.10.19 on this
PC; the full interpreter matrix is for the lens d re-check.

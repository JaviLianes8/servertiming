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
- [ ] Five QA lenses (item 19, run after this stage)
- [ ] Independent reviewer (item 16, run after this stage)

## Scorecard

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: seven names kept from 0.2.0, signatures pinned by `tests/test_contract_api.py`; every change in CHANGELOG and GUIDE |
| 2 | `__all__` exact, no private imports in docs | PASS |
| 3 | Docstrings with runnable examples, doctests | PASS: 16 doctests; README (9 outputs) and GUIDE (11) examples run as tests |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed`, typing checked from a consumer snippet, also against the installed wheel |
| 5 | Typed, documented, bounded errors | PASS: `ServerTimingError` (a `ValueError`) with `position` and `field`, `TypeError` for wrong types, messages quote at most 60 characters |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: W3C, RFC 9110, HTML and Fetch fetched at fixed revisions, WPT corpus, Chrome 155, Firefox 158 and WebKit driven over HTTP |
| 8 | Real e2e from the wheel | PASS: built wheel installed in a throwaway venv, used from an empty folder, command driven by subprocess; no PyPI release to upgrade from |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t; 3.8.20 and 3.9.25 refused by `requires-python` |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links, badge |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-19 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending (next stage) |
| 17 | PR and trace guard | PR from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: author round of 30 mutants, all killed (one after a contract was added) |
| 19 | Five independent QA lenses | pending (next stage) |

## Name

PyPI refused `servertiming`. The new name `timingheader` was checked on 2026-10-20:
`https://pypi.org/pypi/<name>/json` answers 404 for `timingheader`, `timing-header`,
`timing_header`, `timing.header`, `timingheaders`, `timing-headers`, `timing_headers`,
`timing.headers`, `tlmlngheader`, `t1m1ngheader` and `tImIngheader`, and
`pypi.org/simple/timingheader/` is 404. The distribution, the import package, the
command, the tests, the docs and the project URLs use it; the old name appears in one
CHANGELOG line. The GitHub repository and the local folder keep the old name until the
maintainer renames them at merge.

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

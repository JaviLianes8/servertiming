# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## 1.0.0 - 2026-10-20

The public API is now stable: the seven names in `timingheader.__all__`, their
signatures, defaults and error types follow Semantic Versioning from this release on.
This is the first release on PyPI.

### Stable

- Parsing: `parse` reads one or several field values (headers then trailers) the way
  browsers do and never raises on malformed text; `strict=True` checks each value
  against the grammar with the sender rules.
- Building: `build` and `str(metric)` never write a value that could split or corrupt the
  response header.
- `Metric`, the frozen value both sides use.
- Recording: `Timing` with `add`, `measure` (block or decorator, plain or `async`),
  `start`, `metrics` and `header`; `Measure` and `Timer`.
- Errors: `ServerTimingError` (a `ValueError`) for a value that cannot be written or
  breaks the grammar, with `field` and `position` from strict parsing; `TypeError` for an
  argument of the wrong type.
- The `timingheader` command and `python -m timingheader`.

### Changed

- The distribution, the import package and the command are named `timingheader`, and the
  project links point at https://github.com/JaviLianes8/timingheader.
- Developed as `servertiming` up to 0.2.0, a name PyPI does not accept.
- `build`, `str(metric)` and `Timing` raise `TypeError` (they raised
  `ServerTimingError`) for an argument of the wrong type: a single `Metric` or a `str`
  instead of an iterable, an item that is not a `Metric`, a name, description or
  parameter that is not a `str`, a duration that is not an `int` or a `float` (a `bool`
  included), a parameter that is not a `(name, value)` pair, a `precision` that is not an
  `int`.
- `precision` accepts 0 to 20; a larger value raises `ServerTimingError` (a huge one
  raised a bare `ValueError` from the string formatter).
- `Metric.param` raises `TypeError` for a name that is not a `str` (it raised
  `AttributeError`).
- Parameter names are lowered in ASCII only: a name holding the Kelvin sign is no longer
  turned into `k` and written as if it were a token; `build` refuses it.
- `Metric` stores a list of parameters as a tuple, so the metric stays hashable.
- `Timing.measure` refuses a generator function with `TypeError` (calling one only
  creates the generator, so the time recorded was meaningless) and an object that is not
  callable; `Timing` refuses a `clock` that is not callable.
- Error messages quote at most a short excerpt of the value: a 100,000 character name no
  longer comes back whole, and an `int` duration too large for a float no longer raises a
  bare `ValueError` from `repr`.
- Every public name reports `timingheader` as its module (`build` and the property
  getters too), so reprs and pickles never name a private module. The package no longer
  exposes its internal helpers under public names: the names in `dir(timingheader)`
  without a leading underscore are exactly `__all__`.
- A `with timing.measure(...)` block no longer leaves a context variable behind: every
  `Measure` shares one, so a long-lived thread (a WSGI worker, a script's main thread) no
  longer grows by about 120 bytes per request.
- Leaving a `Measure` block in another thread or task than the one that entered it, or
  without entering it, raises `RuntimeError` (it raised an internal `ValueError`). This
  holds for a context copied after the enter too (another asyncio task,
  `asyncio.to_thread`, every new thread on free-threaded Python 3.14): the exit there
  succeeded, and the exit where the block began recorded the metric a second time. A
  block ends once: a second exit through a copy of its context raises `RuntimeError`.
- A clock reading that is an `int` too large for a float raises `ServerTimingError` where
  the measurement ends, as a duration that is not finite does (it raised
  `OverflowError`); nothing is recorded and a `Timer` keeps running. An exception raised
  by the clock itself, `OverflowError` included, is not caught and reaches the caller.
- `typing.get_type_hints` and `inspect.signature(..., eval_str=True)` resolve the
  annotations of `parse` and of the `Measure` and `Timer` constructors (they raised
  `NameError`).
- A clock reading that makes a duration infinite or NaN raises `ServerTimingError` where
  the measurement ends, and nothing is recorded (it was recorded, and every later
  `header()` failed).
- The `Measure` and `Timer` constructors check their arguments as `Timing.measure` and
  `Timing.start` do: a name that is not a token or a description holding a control
  character raises `ServerTimingError`, a `timing` that is not a `Timing` or a `start`
  that is not a number raises `TypeError`.
- A `str` subclass is checked and written as its real characters: one whose iteration or
  formatting hid a CR or LF could reach the header through `build`, `str(metric)` or
  `Timing`.
- The command reads response headers with many folded lines in linear time.
- The command reads only the last response of a header dump that holds several (as
  `curl -sIL` prints redirects); it joined the fields of every response.
- `timingheader --json` escapes every character outside ASCII, so its output is valid
  JSON whatever the console can encode (a Windows pipe produced an invalid `\x85`
  escape).
- An invalid value given on the command line is numbered by its place among the
  arguments, blank ones included.
- The command ends quietly when its reader closes the output early (`| head`), with the
  exit status of the values, instead of printing a `BrokenPipeError` traceback.
- Durations are written with an exponent without a plus sign or leading zeros: `1e-5`
  and `1e16` (they were written `1e-05` and `1e+16`). Both forms read back as the same
  double.
- An `int` duration beyond the range of a float is stored in `Metric` as an infinity of
  its sign, so `Metric.dur` and `Metric.duration` are always a `float` or `None` and
  `repr(metric)` works (it kept the `int`; `repr` raised `ValueError` past 4300 digits).
  `build` refuses it with `ServerTimingError`, as before.
- The `Metric` constructor is typed to take `params` as a list of pairs as well as a
  tuple, as it always did at run time; the field stays a tuple.
- `Metric.param` raises `TypeError` when `params` does not hold `(name, value)` pairs with
  a `str` name (it raised `ValueError` or `AttributeError`).
- `precision` given as a subclass of `int` is used as its exact `int` value, so its
  methods cannot get around the range check.
- A `TypeError` about an `int` subclass in a name, description or parameter name is
  raised as documented even when the subclass overrides `abs` or `bit_length`.
- Entering and leaving nested `Measure` blocks takes the same time at any depth, and
  blocks left open no longer slow later blocks in the same context (both grew with the
  number of running blocks, so deep nesting took quadratic time).
- The command runs with no stdout at all (`pythonw`, a service, file descriptor 1 closed)
  as if its reader had stopped: it checks the values and exits with their status (it
  printed an `AttributeError` traceback and exited with 1).

### Added

- Every public name has a docstring with a runnable example.
- A guide (`GUIDE.md`) describing every rule, and the differences measured between real
  browsers on malformed headers.

## 0.2.0 - 2026-10-13

### Changed

- `parse` reads values the way browsers do and passes the web-platform-tests corpus: a
  metric name must be a token, characters after a name or a value up to the next `;` or
  `,` are ignored, parameter names are case-insensitive, the first occurrence of a
  parameter wins, `dur` may be quoted, and an unterminated quoted string reads as empty.
- `dur` is read with the HTML rules for floating-point numbers (`12ms` is 12, `inf` is no
  duration).
- `parse` keeps extension parameters in `Metric.params` instead of dropping them.
- `build` raises `ServerTimingError` (a `ValueError`) for a description or parameter value
  holding CR, LF or another character no HTTP field can carry, closing a header injection.
- `Timing` checks names and descriptions when a metric is recorded, not when the header
  is rendered.
- `Metric` stores parameter names in lower case and an `int` duration as a `float`, so a
  metric equals what `parse` reads back from its serialization.

### Added

- `parse(header, strict=True)` checks values against the grammar with the sender rules
  (no empty list elements, no repeated parameter) and raises `ServerTimingError` with
  `field` and `position`.
- `parse` accepts several field values (headers then trailers).
- `Metric.params`, `Metric.param()`, `Metric.duration`, `Metric.description` and
  `str(metric)`.
- `build(..., precision=n)` and `Timing.header(precision=n)` round durations.
- `Timing.measure` decorates plain and `async` functions; `Timing.start` returns a `Timer`.
- The `servertiming` command shows and checks values from arguments or response headers.

## 0.1.0 - 2026-10-12

- First release: `build` and `parse` for the Server-Timing header, a `Metric` value
  type, and a `Timing` collector with a `measure` context manager.
